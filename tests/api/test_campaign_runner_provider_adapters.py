"""Tests for provider adapter injection in CampaignRunnerAPI."""

from datetime import UTC, datetime
from types import SimpleNamespace

from api.campaign_runner import CampaignRunnerAPI
from services.campaign_queue import CampaignQueueService, ExecutionQueue
from services.in_memory_provider import InMemoryProviderExecutionAdapter
from services.persistent_queue import PersistentQueue
from services.provider_execution import ExecutionApproval, ExecutionRequest

NOW = datetime(2026, 8, 4, 20, tzinfo=UTC)
CAMPAIGN_ID = "no-lose-guard-launch"


class Store:
    def __init__(self, value) -> None:
        self.value = value
        self.saved = []

    def load(self, *_args):
        return self.value

    def save(self, value) -> None:
        self.saved.append(value)


class Runtime:
    def __init__(self) -> None:
        self.adapters = None
        self.calls = 0

    def advance(
        self,
        campaign_id,
        _run_store,
        _checkpoint_store,
        queue,
        history,
        adapters,
        *,
        worker_id,
        now,
    ):
        self.calls += 1
        self.adapters = adapters
        return SimpleNamespace(
            uncertain=False,
            checkpoint=None,
            result=SimpleNamespace(
                action="execution-completed",
                run=SimpleNamespace(stage="ready"),
                request_id="request-1",
                paused=False,
                queue=queue,
                history=history,
            ),
        )


def run(*, stage: str = "in-production"):
    return SimpleNamespace(
        campaign_id=CAMPAIGN_ID,
        work_id="no-lose-guard",
        stage=stage,
        plan=SimpleNamespace(work_name="No Lose Guard"),
    )


def queued_request(*, provider: str = "in-memory", media_type: str = "image"):
    request = ExecutionRequest(
        request_id="request-1",
        asset_id="asset-1",
        work_id="no-lose-guard",
        media_type=media_type,
        provider=provider,
        prompt="Create a release visual",
    )
    approval = ExecutionApproval(
        asset_id="asset-1",
        media_type=media_type,
        provider=provider,
        approved_by="Kelvin",
    )
    queue = CampaignQueueService().schedule(
        ExecutionQueue(),
        request,
        approval,
        scheduled_for=NOW,
    )
    return PersistentQueue(queue=queue)


def api(*, queue_state, adapters=()):
    runtime = Runtime()
    instance = CampaignRunnerAPI(
        SimpleNamespace(root=None),
        run_store=Store(run()),
        queue_store=Store(queue_state),
        history_store=Store(SimpleNamespace()),
        checkpoint_store=Store(()),
        runtime=runtime,
        preflight=lambda _campaign: None,
        adapters=adapters,
    )
    return instance, runtime


def test_matching_adapter_is_passed_to_runtime() -> None:
    adapter = InMemoryProviderExecutionAdapter()
    instance, runtime = api(queue_state=queued_request(), adapters=(adapter,))

    result = instance.advance(CAMPAIGN_ID, now=NOW)

    assert result.successful is True
    assert result.action == "execution-completed"
    assert runtime.calls == 1
    assert runtime.adapters == (adapter,)


def test_missing_adapter_blocks_due_provider_work() -> None:
    instance, runtime = api(queue_state=queued_request())

    result = instance.advance(CAMPAIGN_ID, now=NOW)

    assert result.successful is False
    assert result.errors == ("provider execution requires configured adapters: in-memory/image",)
    assert runtime.calls == 0


def test_adapter_with_wrong_media_type_blocks_execution() -> None:
    adapter = InMemoryProviderExecutionAdapter(media_types=("video",))
    instance, runtime = api(queue_state=queued_request(), adapters=(adapter,))

    result = instance.advance(CAMPAIGN_ID, now=NOW)

    assert result.errors == ("provider execution requires configured adapters: in-memory/image",)
    assert runtime.calls == 0


def test_adapter_with_wrong_provider_blocks_execution() -> None:
    adapter = InMemoryProviderExecutionAdapter(provider="other")
    instance, runtime = api(queue_state=queued_request(), adapters=(adapter,))

    result = instance.advance(CAMPAIGN_ID, now=NOW)

    assert result.errors == ("provider execution requires configured adapters: in-memory/image",)
    assert runtime.calls == 0


def test_unrelated_due_work_does_not_require_campaign_adapter() -> None:
    state = queued_request()
    unrelated = tuple(
        SimpleNamespace(
            request=SimpleNamespace(
                work_id="another-work",
                provider=job.request.provider,
                media_type=job.request.media_type,
            )
        )
        for job in state.queue.jobs
    )
    queue_service = SimpleNamespace(ready=lambda _queue, *, now: unrelated)
    runtime = Runtime()
    instance = CampaignRunnerAPI(
        SimpleNamespace(root=None),
        run_store=Store(run()),
        queue_store=Store(state),
        history_store=Store(SimpleNamespace()),
        checkpoint_store=Store(()),
        runtime=runtime,
        queue_service=queue_service,
        preflight=lambda _campaign: None,
    )

    result = instance.advance(CAMPAIGN_ID, now=NOW)

    assert result.successful is True
    assert runtime.calls == 1
