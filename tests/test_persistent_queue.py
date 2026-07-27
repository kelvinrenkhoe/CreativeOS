from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from services.campaign_queue import CampaignQueueService, ExecutionQueue
from services.operations_dashboard import AuditHistory
from services.persistent_queue import (
    JsonExecutionQueueStore,
    PersistentQueue,
    QueueStateError,
)
from services.provider_execution import (
    ExecutionApproval,
    ExecutionReceipt,
    ExecutionRequest,
)
from services.queue_worker import QueueWorkerService

NOW = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
LEASE_TIME = timedelta(minutes=5)


@dataclass
class FakeAdapter:
    provider: str = "open-video"
    media_types: tuple[str, ...] = ("video",)

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        return ()

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id="generation-123",
        )


def queue(*request_ids: str) -> ExecutionQueue:
    queued = ExecutionQueue()
    service = CampaignQueueService()
    for request_id in request_ids:
        queued = service.schedule(
            queued,
            ExecutionRequest(
                request_id=request_id,
                asset_id=f"asset-{request_id}",
                work_id="no-lose-guard",
                media_type="video",
                provider="open-video",
                prompt="A cinematic performance scene.",
            ),
            ExecutionApproval(
                asset_id=f"asset-{request_id}",
                media_type="video",
                provider="open-video",
                approved_by="Kelvin",
            ),
            scheduled_for=NOW,
        )
    return queued


def store(path: Path, *request_ids: str) -> JsonExecutionQueueStore:
    result = JsonExecutionQueueStore(path)
    result.save(PersistentQueue(queue=queue(*request_ids)))
    return result


def test_round_trips_complete_queue_and_lease_state(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    saved = store(path, "video-01")
    leased = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )

    restored = JsonExecutionQueueStore(path).load()

    assert leased is not None
    assert restored == leased.state
    assert restored.queue.jobs[0].approval.approved_by == "Kelvin"
    assert restored.leases[0].expires_at == NOW + LEASE_TIME


def test_two_store_instances_cannot_lease_the_same_request(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    first = store(path, "video-01")
    second = JsonExecutionQueueStore(path)

    leased = first.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )
    blocked = second.lease_next(
        worker_id="worker-2",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-02",
    )

    assert leased is not None
    assert blocked is None
    assert second.load().leases == (leased.lease,)


def test_different_workers_receive_different_ready_jobs(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    saved = store(path, "video-01", "video-02")

    first = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )
    second = saved.lease_next(
        worker_id="worker-2",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-02",
    )

    assert first is not None
    assert second is not None
    assert first.lease.request_id == "video-01"
    assert second.lease.request_id == "video-02"


def test_expired_lease_makes_request_available_again(tmp_path: Path) -> None:
    saved = store(tmp_path / "queue.json", "video-01")
    first = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )

    reclaimed = saved.lease_next(
        worker_id="worker-2",
        now=NOW + LEASE_TIME,
        lease_for=LEASE_TIME,
        lease_id="lease-02",
    )

    assert first is not None
    assert reclaimed is not None
    assert reclaimed.lease.request_id == first.lease.request_id
    assert reclaimed.lease.worker_id == "worker-2"


def test_matching_lease_commits_worker_result_and_clears_ownership(
    tmp_path: Path,
) -> None:
    saved = store(tmp_path / "queue.json", "video-01")
    leased = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )
    assert leased is not None
    result = QueueWorkerService().run_next(
        leased.state.queue,
        AuditHistory(),
        (FakeAdapter(),),
        worker_id="worker-1",
        now=NOW,
    )

    committed = saved.commit(leased.lease, result.queue, now=NOW)

    assert committed.queue.jobs[0].status == "completed"
    assert committed.queue.jobs[0].receipt.external_id == "generation-123"
    assert committed.leases == ()
    assert saved.load() == committed


def test_expired_or_wrong_worker_lease_cannot_commit(tmp_path: Path) -> None:
    saved = store(tmp_path / "queue.json", "video-01")
    leased = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )
    assert leased is not None
    result = QueueWorkerService().run_next(
        leased.state.queue,
        AuditHistory(),
        (FakeAdapter(),),
        worker_id="worker-1",
        now=NOW,
    )

    with pytest.raises(PermissionError, match="identity"):
        saved.commit(
            leased.lease.__class__(
                lease_id=leased.lease.lease_id,
                request_id=leased.lease.request_id,
                worker_id="worker-2",
                acquired_at=leased.lease.acquired_at,
                expires_at=leased.lease.expires_at,
            ),
            result.queue,
            now=NOW,
        )

    with pytest.raises(PermissionError, match="missing or expired"):
        saved.commit(leased.lease, result.queue, now=NOW + LEASE_TIME)


def test_lease_can_be_renewed_or_released_without_changing_queue(
    tmp_path: Path,
) -> None:
    saved = store(tmp_path / "queue.json", "video-01")
    leased = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )
    assert leased is not None

    renewed = saved.renew(
        leased.lease,
        now=NOW + timedelta(minutes=1),
        lease_for=LEASE_TIME,
    )
    released = saved.release(renewed, now=NOW + timedelta(minutes=2))

    assert renewed.expires_at == NOW + timedelta(minutes=6)
    assert released.leases == ()
    assert released.queue.jobs[0].status == "scheduled"


def test_rejects_unknown_snapshot_version_and_non_terminal_commit(
    tmp_path: Path,
) -> None:
    path = tmp_path / "queue.json"
    path.write_text('{"version": 99, "jobs": [], "leases": []}', encoding="utf-8")

    with pytest.raises(QueueStateError, match="version"):
        JsonExecutionQueueStore(path).load()

    saved = store(path, "video-01")
    leased = saved.lease_next(
        worker_id="worker-1",
        now=NOW,
        lease_for=LEASE_TIME,
        lease_id="lease-01",
    )
    assert leased is not None

    with pytest.raises(QueueStateError, match="completed or failed"):
        saved.commit(leased.lease, leased.state.queue, now=NOW)
