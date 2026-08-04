"""Structured API for advancing one durable campaign runtime action."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.project import Project
from orchestrator import CampaignRuntimePreset, CampaignRuntimePresetRegistry, RuntimeStage
from services.audit_history_store import JsonAuditHistoryStore
from services.campaign_doctor import CampaignDoctorService
from services.campaign_queue import CampaignQueueService
from services.campaign_run_state import JsonCampaignRunStore
from services.persistent_queue import JsonExecutionQueueStore, PersistentQueue
from services.runtime_checkpoints import (
    CheckpointedCampaignRuntime,
    JsonRuntimeCheckpointStore,
)

RUNTIME_PATH = Path(".creativeos") / "runtime"
CAMPAIGN_RUNS_PATH = RUNTIME_PATH / "campaign-runs"
QUEUE_PATH = RUNTIME_PATH / "execution-queue.json"
AUDIT_HISTORY_PATH = RUNTIME_PATH / "audit-history.json"
CHECKPOINTS_PATH = RUNTIME_PATH / "campaign-checkpoints.json"
DEFAULT_WORKER_ID = "creativeos-api"


@dataclass(frozen=True, slots=True)
class CampaignRunnerResult:
    """Structured result from advancing one campaign runtime action."""

    campaign_id: str
    stage: str | None = None
    action: str | None = None
    request_id: str | None = None
    paused: bool = False
    uncertain: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether the runtime action completed without errors."""
        return not self.errors


class CampaignRunnerAPI:
    """Advance at most one safe action for a persisted campaign runtime."""

    def __init__(
        self,
        project: Project,
        *,
        run_store=None,
        queue_store=None,
        history_store=None,
        checkpoint_store=None,
        runtime=None,
        queue_service=None,
        preflight=None,
        worker_id: str = DEFAULT_WORKER_ID,
    ) -> None:
        self.project = project
        self.run_store = run_store or JsonCampaignRunStore(
            project.root / CAMPAIGN_RUNS_PATH
        )
        self.queue_store = queue_store or JsonExecutionQueueStore(project.root / QUEUE_PATH)
        self.history_store = history_store or JsonAuditHistoryStore(
            project.root / AUDIT_HISTORY_PATH
        )
        self.checkpoint_store = checkpoint_store or JsonRuntimeCheckpointStore(
            project.root / CHECKPOINTS_PATH
        )
        self.runtime = runtime or CheckpointedCampaignRuntime()
        self.queue_service = queue_service or CampaignQueueService()
        self.preflight = preflight or self._validate_preflight
        self.worker_id = worker_id

    def advance(
        self,
        campaign_id: str,
        *,
        now: datetime | None = None,
    ) -> CampaignRunnerResult:
        """Advance one safe runtime action and persist changed durable state."""
        reference_time = now or datetime.now(UTC)

        try:
            run = self.run_store.load(campaign_id)
            self.preflight(run.plan.work_name)

            queue_state = self.queue_store.load()
            history = self.history_store.load()
            due = self.queue_service.ready(queue_state.queue, now=reference_time)
            if run.stage == "in-production" and any(
                job.request.work_id == run.work_id for job in due
            ):
                return CampaignRunnerResult(
                    campaign_id=campaign_id,
                    stage=run.stage,
                    errors=(
                        "provider execution requires explicit provider configuration",
                    ),
                )

            outcome = self.runtime.advance(
                campaign_id,
                self.run_store,
                self.checkpoint_store,
                queue_state.queue,
                history,
                (),
                worker_id=self.worker_id,
                now=reference_time,
            )
            if outcome.uncertain:
                return CampaignRunnerResult(
                    campaign_id=campaign_id,
                    stage=run.stage,
                    uncertain=True,
                    errors=(
                        "runtime action is uncertain; reconcile it before retrying",
                    ),
                )

            if outcome.result is None:
                checkpoint = outcome.checkpoint
                if checkpoint is None or checkpoint.status != "completed":
                    return CampaignRunnerResult(
                        campaign_id=campaign_id,
                        stage=run.stage,
                        errors=("runtime produced no reportable outcome",),
                    )
                action = checkpoint.result_action or "completed"
                stage = checkpoint.resulting_stage or run.stage
                request_id = checkpoint.request_id
                paused = action.startswith("awaiting-") or action in {
                    "execution-failed",
                    "completed",
                }
            else:
                result = outcome.result
                action = result.action
                stage = result.run.stage
                request_id = result.request_id
                paused = result.paused
                if result.queue != queue_state.queue:
                    self.queue_store.save(
                        PersistentQueue(queue=result.queue, leases=queue_state.leases)
                    )
                if result.history != history:
                    self.history_store.save(result.history)

            return CampaignRunnerResult(
                campaign_id=campaign_id,
                stage=stage,
                action=action,
                request_id=request_id,
                paused=paused,
            )
        except (OSError, PermissionError, ValueError) as exc:
            return CampaignRunnerResult(
                campaign_id=campaign_id,
                errors=(str(exc),),
            )

    def _validate_preflight(self, campaign_name: str) -> None:
        """Block runtime advancement when campaign readiness checks fail."""
        registry = CampaignRuntimePresetRegistry()
        registry.register(
            CampaignRuntimePreset(
                name="music-release",
                description="Validate a music-release campaign before execution.",
                required_context_keys=("campaign",),
                stages=(
                    RuntimeStage(
                        "brief",
                        lambda campaign: campaign,
                        ("campaign",),
                        "brief",
                    ),
                ),
            )
        )
        report = CampaignDoctorService(self.project, registry).diagnose(
            campaign_name,
            context={"campaign": campaign_name},
        )
        if report.healthy:
            return

        failures = ", ".join(check.name for check in report.checks if check.failed)
        raise ValueError(
            f'campaign readiness preflight failed for "{campaign_name}": '
            f"{failures}. Run: creativeos doctor --campaign "
            f'"{campaign_name}"'
        )
