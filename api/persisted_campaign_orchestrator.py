"""Durable wrapper around bounded campaign orchestration."""

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from api.campaign_orchestrator import CampaignOrchestrationResult, CampaignOrchestratorAPI
from services.campaign_orchestration_events import JsonOrchestrationEventStore

ORCHESTRATION_EVENTS_PATH = Path(".creativeos") / "runtime" / "orchestration-events"


class PersistedCampaignOrchestratorAPI:
    """Run bounded orchestration and persist its complete ordered event history."""

    def __init__(
        self,
        orchestrator: CampaignOrchestratorAPI,
        event_store: JsonOrchestrationEventStore | None,
        *,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.event_store = event_store
        self.run_id_factory = run_id_factory or (lambda: uuid4().hex)

    @classmethod
    def for_project(
        cls,
        project,
        orchestrator: CampaignOrchestratorAPI,
        *,
        run_id_factory: Callable[[], str] | None = None,
    ) -> "PersistedCampaignOrchestratorAPI":
        """Build the standard project-scoped orchestration event store when possible."""
        root = getattr(project, "root", None)
        event_store = (
            JsonOrchestrationEventStore(root / ORCHESTRATION_EVENTS_PATH)
            if isinstance(root, Path)
            else None
        )
        return cls(orchestrator, event_store, run_id_factory=run_id_factory)

    def run(
        self,
        campaign_id: str,
        *,
        run_id: str | None = None,
        **run_options,
    ) -> CampaignOrchestrationResult:
        """Run orchestration and atomically append its events when storage is configured."""
        result = self.orchestrator.run(campaign_id, **run_options)
        if self.event_store is not None:
            self.event_store.append(
                campaign_id=result.campaign_id,
                run_id=run_id or self.run_id_factory(),
                policy=result.policy,
                events=result.events,
            )
        return result
