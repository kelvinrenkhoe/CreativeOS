"""Durable wrapper around bounded campaign orchestration."""

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from api.campaign_orchestrator import CampaignOrchestrationResult, CampaignOrchestratorAPI
from services.campaign_orchestration_events import JsonOrchestrationEventStore
from services.campaign_runtime_lock import JsonCampaignRuntimeLockStore

ORCHESTRATION_EVENTS_PATH = Path(".creativeos") / "runtime" / "orchestration-events"
RUNTIME_LOCKS_PATH = Path(".creativeos") / "runtime" / "campaign-locks"


class PersistedCampaignOrchestratorAPI:
    """Run bounded orchestration with durable history and campaign-scoped locking."""

    def __init__(
        self,
        orchestrator: CampaignOrchestratorAPI,
        event_store: JsonOrchestrationEventStore | None,
        *,
        lock_store: JsonCampaignRuntimeLockStore | None = None,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.event_store = event_store
        self.lock_store = lock_store
        self.run_id_factory = run_id_factory or (lambda: uuid4().hex)

    @classmethod
    def for_project(
        cls,
        project,
        orchestrator: CampaignOrchestratorAPI,
        *,
        run_id_factory: Callable[[], str] | None = None,
    ) -> "PersistedCampaignOrchestratorAPI":
        """Build the standard project-scoped event and lock stores when possible."""
        root = getattr(project, "root", None)
        event_store = None
        lock_store = None
        if isinstance(root, Path):
            event_store = JsonOrchestrationEventStore(root / ORCHESTRATION_EVENTS_PATH)
            lock_store = JsonCampaignRuntimeLockStore(root / RUNTIME_LOCKS_PATH)
        return cls(
            orchestrator,
            event_store,
            lock_store=lock_store,
            run_id_factory=run_id_factory,
        )

    def run(
        self,
        campaign_id: str,
        *,
        run_id: str | None = None,
        **run_options,
    ) -> CampaignOrchestrationResult:
        """Run and persist one bounded orchestration while holding its campaign lock."""
        resolved_run_id = run_id or self.run_id_factory()
        if self.lock_store is not None:
            self.lock_store.acquire(campaign_id, resolved_run_id)

        try:
            result = self.orchestrator.run(campaign_id, **run_options)
            if self.event_store is not None:
                self.event_store.append(
                    campaign_id=result.campaign_id,
                    run_id=resolved_run_id,
                    policy=result.policy,
                    events=result.events,
                )
            return result
        finally:
            if self.lock_store is not None:
                self.lock_store.release(campaign_id, resolved_run_id)
