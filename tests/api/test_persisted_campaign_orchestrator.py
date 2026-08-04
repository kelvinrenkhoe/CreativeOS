"""Tests for persisted bounded campaign orchestration."""

from types import SimpleNamespace

from api.persisted_campaign_orchestrator import (
    ORCHESTRATION_EVENTS_PATH,
    PersistedCampaignOrchestratorAPI,
)
from services.campaign_orchestration_events import JsonOrchestrationEventStore


class StubOrchestrator:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def run(self, campaign_id: str, **options):
        self.calls.append((campaign_id, options))
        return self.result


def result():
    event = SimpleNamespace(
        kind="campaign-started",
        step=0,
        campaign_id="campaign-1",
        stage=None,
        action=None,
        request_id=None,
        detail="once",
    )
    return SimpleNamespace(campaign_id="campaign-1", policy="once", events=(event,))


def test_run_persists_ordered_events_with_explicit_run_id(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)
    orchestrator = StubOrchestrator(result())
    api = PersistedCampaignOrchestratorAPI(orchestrator, store)

    returned = api.run("campaign-1", run_id="run-1", max_steps=7)

    assert returned is orchestrator.result
    assert orchestrator.calls == [("campaign-1", {"max_steps": 7})]
    history = store.load("campaign-1")
    assert [item.run_id for item in history] == ["run-1"]
    assert [item.kind for item in history] == ["campaign-started"]


def test_run_uses_injected_run_id_factory(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)
    api = PersistedCampaignOrchestratorAPI(
        StubOrchestrator(result()),
        store,
        run_id_factory=lambda: "generated-run",
    )

    api.run("campaign-1")

    assert store.load("campaign-1")[0].run_id == "generated-run"


def test_for_project_uses_standard_runtime_directory(tmp_path) -> None:
    project = SimpleNamespace(root=tmp_path)
    api = PersistedCampaignOrchestratorAPI.for_project(
        project,
        StubOrchestrator(result()),
        run_id_factory=lambda: "run-1",
    )

    api.run("campaign-1")

    history_path = tmp_path / ORCHESTRATION_EVENTS_PATH / "campaign-1.json"
    assert history_path.exists()


def test_project_without_path_keeps_injected_cli_tests_storage_free() -> None:
    orchestrator = StubOrchestrator(result())
    api = PersistedCampaignOrchestratorAPI.for_project(object(), orchestrator)

    returned = api.run("campaign-1")

    assert returned is orchestrator.result
    assert api.event_store is None
