"""Tests for locking around persisted campaign orchestration."""

from types import SimpleNamespace

import pytest

from api.persisted_campaign_orchestrator import (
    RUNTIME_LOCKS_PATH,
    PersistedCampaignOrchestratorAPI,
)


class StubOrchestrator:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or SimpleNamespace(
            campaign_id="campaign-1",
            policy="once",
            events=(),
        )
        self.error = error

    def run(self, campaign_id: str, **options):
        if self.error is not None:
            raise self.error
        return self.result


class RecordingLockStore:
    def __init__(self) -> None:
        self.calls = []

    def acquire(self, campaign_id: str, owner_id: str) -> None:
        self.calls.append(("acquire", campaign_id, owner_id))

    def release(self, campaign_id: str, owner_id: str) -> None:
        self.calls.append(("release", campaign_id, owner_id))


def test_run_holds_and_releases_lock_for_resolved_run_id() -> None:
    locks = RecordingLockStore()
    api = PersistedCampaignOrchestratorAPI(
        StubOrchestrator(),
        None,
        lock_store=locks,
        run_id_factory=lambda: "run-1",
    )

    api.run("campaign-1")

    assert locks.calls == [
        ("acquire", "campaign-1", "run-1"),
        ("release", "campaign-1", "run-1"),
    ]


def test_run_releases_lock_when_orchestration_raises() -> None:
    locks = RecordingLockStore()
    api = PersistedCampaignOrchestratorAPI(
        StubOrchestrator(error=RuntimeError("boom")),
        None,
        lock_store=locks,
        run_id_factory=lambda: "run-1",
    )

    with pytest.raises(RuntimeError, match="boom"):
        api.run("campaign-1")

    assert locks.calls[-1] == ("release", "campaign-1", "run-1")


def test_for_project_configures_standard_runtime_lock_directory(tmp_path) -> None:
    api = PersistedCampaignOrchestratorAPI.for_project(
        SimpleNamespace(root=tmp_path),
        StubOrchestrator(),
    )

    assert api.lock_store is not None
    assert api.lock_store.directory == tmp_path / RUNTIME_LOCKS_PATH


def test_project_without_path_keeps_locking_disabled() -> None:
    api = PersistedCampaignOrchestratorAPI.for_project(object(), StubOrchestrator())

    assert api.lock_store is None
