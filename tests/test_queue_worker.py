from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from services.campaign_queue import CampaignQueueService, ExecutionQueue
from services.operations_dashboard import AuditHistory
from services.provider_execution import (
    ExecutionApproval,
    ExecutionReceipt,
    ExecutionRequest,
)
from services.queue_worker import QueueWorkerService, RetryableProviderError

NOW = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


@dataclass
class FakeAdapter:
    provider: str = "open-video"
    media_types: tuple[str, ...] = ("video",)
    failures: list[Exception] = field(default_factory=list)
    calls: int = 0

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        return ()

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id="generation-123",
        )


def queue(request_id: str = "video-01") -> ExecutionQueue:
    return CampaignQueueService().schedule(
        ExecutionQueue(),
        ExecutionRequest(
            request_id=request_id,
            asset_id="no-lose-guard-video-01",
            work_id="no-lose-guard",
            media_type="video",
            provider="open-video",
            prompt="A cinematic performance scene.",
        ),
        ExecutionApproval(
            asset_id="no-lose-guard-video-01",
            media_type="video",
            provider="open-video",
            approved_by="Kelvin",
        ),
        scheduled_for=NOW,
    )


def run(
    queued: ExecutionQueue,
    adapter: FakeAdapter,
    *,
    max_attempts: int = 1,
):
    return QueueWorkerService().run_next(
        queued,
        AuditHistory(),
        (adapter,),
        worker_id="worker-1",
        now=NOW,
        max_attempts=max_attempts,
    )


def test_claims_executes_and_completes_next_ready_job() -> None:
    adapter = FakeAdapter()

    result = run(queue(), adapter)

    assert result.request_id == "video-01"
    assert result.queue.jobs[0].status == "completed"
    assert result.queue.jobs[0].receipt.external_id == "generation-123"
    assert [event.action for event in result.history.events] == ["claimed", "completed"]
    assert result.attempts[0].succeeded is True
    assert adapter.calls == 1


def test_returns_unchanged_state_when_no_work_is_ready() -> None:
    empty = ExecutionQueue()
    history = AuditHistory()

    result = QueueWorkerService().run_next(
        empty,
        history,
        (FakeAdapter(),),
        worker_id="worker-1",
        now=NOW,
    )

    assert result.queue is empty
    assert result.history is history
    assert result.request_id is None


def test_processes_only_one_job_in_deterministic_queue_order() -> None:
    queued = queue("second")
    first = queue("first").jobs[0]
    queued = ExecutionQueue(jobs=(*queued.jobs, first))

    result = run(queued, FakeAdapter())

    statuses = {job.request.request_id: job.status for job in result.queue.jobs}
    assert statuses == {"second": "scheduled", "first": "completed"}


def test_retries_only_explicit_transient_provider_errors() -> None:
    adapter = FakeAdapter(failures=[RetryableProviderError("provider busy")])

    result = run(queue(), adapter, max_attempts=2)

    assert result.queue.jobs[0].status == "completed"
    assert [attempt.succeeded for attempt in result.attempts] == [False, True]
    assert [event.action for event in result.history.events] == [
        "claimed",
        "retryable-failure",
        "completed",
    ]
    assert adapter.calls == 2


def test_records_terminal_failure_after_retry_limit() -> None:
    adapter = FakeAdapter(
        failures=[
            RetryableProviderError("provider busy"),
            RetryableProviderError("provider still busy"),
        ]
    )

    result = run(queue(), adapter, max_attempts=2)

    assert result.queue.jobs[0].status == "failed"
    assert result.queue.jobs[0].failure_reason == "provider still busy"
    assert result.history.events[-1].action == "failed"
    assert adapter.calls == 2


def test_does_not_retry_validation_or_permanent_errors() -> None:
    adapter = FakeAdapter(failures=[ValueError("invalid provider request")])

    result = run(queue(), adapter, max_attempts=3)

    assert result.queue.jobs[0].status == "failed"
    assert result.queue.jobs[0].failure_reason == "invalid provider request"
    assert len(result.attempts) == 1
    assert adapter.calls == 1


def test_fails_safely_when_no_matching_adapter_is_configured() -> None:
    result = QueueWorkerService().run_next(
        queue(),
        AuditHistory(),
        (),
        worker_id="worker-1",
        now=NOW,
    )

    assert result.queue.jobs[0].status == "failed"
    assert "no adapter configured" in result.queue.jobs[0].failure_reason
    assert result.history.events[-1].action == "failed"


def test_rejects_invalid_worker_configuration_before_claiming() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        run(queue(), FakeAdapter(), max_attempts=0)

    with pytest.raises(ValueError, match="worker_id"):
        QueueWorkerService().run_next(
            queue(),
            AuditHistory(),
            (FakeAdapter(),),
            worker_id=" ",
            now=NOW,
        )
