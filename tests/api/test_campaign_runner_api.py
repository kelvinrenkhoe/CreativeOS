"""Tests for the structured campaign runner API."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from api.campaign_runner import CampaignRunnerAPI
from core.project import Project

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
repository:
  songs: songs
  campaigns: campaigns
  assets: assets
  knowledge: knowledge
"""


def project(root: Path) -> Project:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir()
    return Project(root)


class Store:
    def __init__(self, value) -> None:
        self.value = value
        self.saved = []

    def load(self, *_args):
        return self.value

    def save(self, value) -> None:
        self.saved.append(value)


class Runtime:
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.calls = []

    def advance(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.outcome


class QueueService:
    def __init__(self, due=()) -> None:
        self.due = due
        self.reference_time = None

    def ready(self, _queue, *, now):
        self.reference_time = now
        return self.due


def runner(tmp_path: Path, *, outcome, run=None, due=(), preflight=None):
    run = run or SimpleNamespace(
        stage="brief",
        work_id="work-1",
        plan=SimpleNamespace(work_name="No Lose Guard"),
    )
    queue = object()
    history = object()
    queue_state = SimpleNamespace(queue=queue, leases=("lease",))
    run_store = Store(run)
    queue_store = Store(queue_state)
    history_store = Store(history)
    checkpoint_store = Store(())
    runtime = Runtime(outcome)
    queue_service = QueueService(due)
    checked = []

    def default_preflight(name: str) -> None:
        checked.append(name)

    api = CampaignRunnerAPI(
        project(tmp_path),
        run_store=run_store,
        queue_store=queue_store,
        history_store=history_store,
        checkpoint_store=checkpoint_store,
        runtime=runtime,
        queue_service=queue_service,
        preflight=preflight or default_preflight,
        worker_id="test-worker",
    )
    return api, SimpleNamespace(
        run_store=run_store,
        queue_store=queue_store,
        history_store=history_store,
        checkpoint_store=checkpoint_store,
        runtime=runtime,
        queue_service=queue_service,
        checked=checked,
        queue=queue,
        history=history,
    )


def test_advance_returns_structured_runtime_result(tmp_path: Path) -> None:
    new_queue = object()
    new_history = object()
    result = SimpleNamespace(
        action="queued",
        run=SimpleNamespace(stage="in-production"),
        request_id="request-1",
        paused=False,
        queue=new_queue,
        history=new_history,
    )
    api, deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=False, result=result, checkpoint=None),
    )
    now = datetime(2026, 8, 4, 20, tzinfo=UTC)

    response = api.advance("campaign-1", now=now)

    assert response.successful
    assert response.action == "queued"
    assert response.stage == "in-production"
    assert response.request_id == "request-1"
    assert not response.paused
    assert deps.checked == ["No Lose Guard"]
    assert deps.queue_service.reference_time == now
    assert deps.queue_store.saved[0].queue is new_queue
    assert deps.history_store.saved == [new_history]


def test_advance_does_not_save_unchanged_state(tmp_path: Path) -> None:
    outcome_result = SimpleNamespace(
        action="waiting",
        run=SimpleNamespace(stage="brief"),
        request_id=None,
        paused=True,
        queue=None,
        history=None,
    )
    api, deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=False, result=None, checkpoint=None),
    )
    outcome_result.queue = deps.queue
    outcome_result.history = deps.history
    deps.runtime.outcome = SimpleNamespace(
        uncertain=False,
        result=outcome_result,
        checkpoint=None,
    )

    response = api.advance("campaign-1")

    assert response.successful
    assert deps.queue_store.saved == []
    assert deps.history_store.saved == []


def test_completed_checkpoint_is_reported_without_rewriting_state(tmp_path: Path) -> None:
    checkpoint = SimpleNamespace(
        status="completed",
        result_action="awaiting-review",
        resulting_stage="review",
        request_id="request-2",
    )
    api, deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=False, result=None, checkpoint=checkpoint),
    )

    response = api.advance("campaign-1")

    assert response.successful
    assert response.action == "awaiting-review"
    assert response.stage == "review"
    assert response.request_id == "request-2"
    assert response.paused
    assert deps.queue_store.saved == []


def test_due_provider_work_is_blocked_without_configuration(tmp_path: Path) -> None:
    run = SimpleNamespace(
        stage="in-production",
        work_id="work-1",
        plan=SimpleNamespace(work_name="No Lose Guard"),
    )
    due = (
        SimpleNamespace(
            request=SimpleNamespace(
                work_id="work-1",
                provider="in-memory",
                media_type="image",
            )
        ),
    )
    api, deps = runner(
        tmp_path,
        run=run,
        due=due,
        outcome=SimpleNamespace(uncertain=False, result=None, checkpoint=None),
    )

    response = api.advance("campaign-1")

    assert not response.successful
    assert response.errors == ("provider execution requires configured adapters: in-memory/image",)
    assert deps.runtime.calls == []


def test_uncertain_outcome_requires_reconciliation(tmp_path: Path) -> None:
    api, _deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=True, result=None, checkpoint=None),
    )

    response = api.advance("campaign-1")

    assert response.uncertain
    assert not response.successful
    assert "reconcile" in response.errors[0]


def test_missing_reportable_outcome_returns_error(tmp_path: Path) -> None:
    api, _deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=False, result=None, checkpoint=None),
    )

    response = api.advance("campaign-1")

    assert not response.successful
    assert response.errors == ("runtime produced no reportable outcome",)


def test_preflight_failure_is_structured(tmp_path: Path) -> None:
    def fail(_name: str) -> None:
        raise ValueError("campaign readiness failed")

    api, deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=False, result=None, checkpoint=None),
        preflight=fail,
    )

    response = api.advance("campaign-1")

    assert not response.successful
    assert response.errors == ("campaign readiness failed",)
    assert deps.runtime.calls == []


def test_reference_time_and_worker_are_forwarded(tmp_path: Path) -> None:
    checkpoint = SimpleNamespace(
        status="completed",
        result_action="completed",
        resulting_stage="completed",
        request_id=None,
    )
    api, deps = runner(
        tmp_path,
        outcome=SimpleNamespace(uncertain=False, result=None, checkpoint=checkpoint),
    )
    now = datetime(2026, 8, 4, 21, tzinfo=UTC)

    api.advance("campaign-1", now=now)

    args, kwargs = deps.runtime.calls[0]
    assert args[0] == "campaign-1"
    assert kwargs["worker_id"] == "test-worker"
    assert kwargs["now"] == now
