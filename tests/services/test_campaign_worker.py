"""Tests for deterministic persisted campaign worker selection."""

from dataclasses import dataclass

from api.campaign_orchestrator import CampaignOrchestrationResult
from services.campaign_worker import TERMINAL_STAGE, CampaignWorkerAPI


@dataclass(frozen=True)
class StubPlan:
    work_name: str


@dataclass(frozen=True)
class StubRun:
    campaign_id: str
    stage: str
    plan: StubPlan


class StubRunStore:
    def __init__(self, runs=()) -> None:
        self.runs = tuple(runs)

    def load_all(self):
        return self.runs


def test_status_separates_pending_and_completed_runs() -> None:
    pending = StubRun("campaign-b", "brief", StubPlan("B"))
    completed = StubRun("campaign-a", TERMINAL_STAGE, StubPlan("A"))
    worker = CampaignWorkerAPI(StubRunStore((pending, completed)), lambda _: None)

    status = worker.status()

    assert status.pending == (pending,)
    assert status.completed == (completed,)
    assert status.idle is False


def test_status_is_idle_when_all_runs_are_terminal() -> None:
    completed = StubRun("campaign-a", TERMINAL_STAGE, StubPlan("A"))
    worker = CampaignWorkerAPI(StubRunStore((completed,)), lambda _: None)

    assert worker.status().idle is True


def test_run_once_returns_idle_without_pending_runs() -> None:
    worker = CampaignWorkerAPI(StubRunStore(), lambda _: None)

    result = worker.run_once()

    assert result.idle is True
    assert result.orchestration is None


def test_run_once_executes_first_pending_run_in_store_order() -> None:
    calls: list[str] = []
    first = StubRun("campaign-a", "brief", StubPlan("A"))
    second = StubRun("campaign-b", "ready", StubPlan("B"))
    orchestration = CampaignOrchestrationResult("campaign-a", "until-blocked", steps=2)
    worker = CampaignWorkerAPI(
        StubRunStore((first, second)),
        lambda campaign_id: calls.append(campaign_id) or orchestration,
    )

    result = worker.run_once()

    assert calls == ["campaign-a"]
    assert result.campaign_id == "campaign-a"
    assert result.orchestration is orchestration
