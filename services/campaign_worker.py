"""Select and advance persisted campaign runs without interactive input."""

from collections.abc import Callable
from dataclasses import dataclass

from api.campaign_orchestrator import (
    POLICY_UNTIL_BLOCKED,
    CampaignOrchestrationResult,
    CampaignOrchestratorAPI,
)
from api.campaign_runner import CampaignRunnerAPI
from api.persisted_campaign_orchestrator import PersistedCampaignOrchestratorAPI
from core.project import Project
from services.campaign_orchestration import STAGES, CampaignRun
from services.campaign_run_state import JsonCampaignRunStore
from services.provider_execution import ProviderExecutionAdapter

WORKER_ID = "creativeos-worker"
TERMINAL_STAGE = STAGES[-1]


@dataclass(frozen=True, slots=True)
class CampaignWorkerStatus:
    """Current deterministic view of persisted campaign work."""

    pending: tuple[CampaignRun, ...]
    completed: tuple[CampaignRun, ...]

    @property
    def idle(self) -> bool:
        return not self.pending


@dataclass(frozen=True, slots=True)
class CampaignWorkerResult:
    """Outcome from one worker polling cycle."""

    campaign_id: str | None = None
    orchestration: CampaignOrchestrationResult | None = None

    @property
    def idle(self) -> bool:
        return self.campaign_id is None


class CampaignWorkerAPI:
    """Advance the first unfinished campaign in deterministic ID order."""

    def __init__(
        self,
        run_store: JsonCampaignRunStore,
        execute: Callable[[str], CampaignOrchestrationResult],
    ) -> None:
        self.run_store = run_store
        self.execute = execute

    @classmethod
    def for_project(
        cls,
        project: Project,
        *,
        adapters: tuple[ProviderExecutionAdapter, ...] = (),
        max_steps: int = 100,
    ) -> "CampaignWorkerAPI":
        """Build a worker from the existing durable runtime boundaries."""
        runner = CampaignRunnerAPI(
            project,
            adapters=adapters,
            worker_id=WORKER_ID,
        )
        orchestrator = CampaignOrchestratorAPI(runner)
        persisted = PersistedCampaignOrchestratorAPI.for_project(project, orchestrator)
        run_store = JsonCampaignRunStore(project.root / ".creativeos/runtime/campaign-runs")

        def execute(campaign_id: str) -> CampaignOrchestrationResult:
            return persisted.run(
                campaign_id,
                policy=POLICY_UNTIL_BLOCKED,
                max_steps=max_steps,
            )

        return cls(run_store, execute)

    def status(self) -> CampaignWorkerStatus:
        """Return unfinished and terminal campaign runs without mutation."""
        runs = self.run_store.load_all()
        pending = tuple(run for run in runs if run.stage != TERMINAL_STAGE)
        completed = tuple(run for run in runs if run.stage == TERMINAL_STAGE)
        return CampaignWorkerStatus(pending=pending, completed=completed)

    def run_once(self) -> CampaignWorkerResult:
        """Advance the first unfinished campaign, or report an idle worker."""
        status = self.status()
        if status.idle:
            return CampaignWorkerResult()
        campaign = status.pending[0]
        return CampaignWorkerResult(
            campaign_id=campaign.campaign_id,
            orchestration=self.execute(campaign.campaign_id),
        )
