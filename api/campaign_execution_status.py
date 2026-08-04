"""Read-only API for persisted campaign provider execution status."""

from dataclasses import dataclass
from pathlib import Path

from core.project import Project
from services.campaign_run_state import JsonCampaignRunStore
from services.persistent_queue import JsonExecutionQueueStore

RUNTIME_PATH = Path(".creativeos") / "runtime"
CAMPAIGN_RUNS_PATH = RUNTIME_PATH / "campaign-runs"
QUEUE_PATH = RUNTIME_PATH / "execution-queue.json"


@dataclass(frozen=True, slots=True)
class CampaignExecutionItem:
    """One persisted provider execution associated with a campaign work ID."""

    request_id: str
    asset_id: str
    media_type: str
    provider: str
    status: str
    external_id: str | None = None
    outputs: tuple[str, ...] = ()
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CampaignExecutionStatusResult:
    """Structured read-only execution status for one persisted campaign."""

    campaign_id: str
    work_id: str | None = None
    items: tuple[CampaignExecutionItem, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def completed(self) -> int:
        return sum(item.status == "completed" for item in self.items)

    @property
    def failed(self) -> int:
        return sum(item.status == "failed" for item in self.items)

    @property
    def pending(self) -> int:
        return self.total - self.completed - self.failed

    @property
    def successful(self) -> bool:
        return not self.errors


class CampaignExecutionStatusAPI:
    """Inspect durable provider execution outcomes without advancing runtime."""

    def __init__(self, project: Project, *, run_store=None, queue_store=None) -> None:
        self.run_store = run_store or JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH)
        self.queue_store = queue_store or JsonExecutionQueueStore(project.root / QUEUE_PATH)

    def status(self, campaign_id: str) -> CampaignExecutionStatusResult:
        """Return deterministic queue and receipt status for one campaign."""
        try:
            run = self.run_store.load(campaign_id)
            queue_state = self.queue_store.load()
        except (OSError, PermissionError, TypeError, ValueError) as exc:
            return CampaignExecutionStatusResult(campaign_id=campaign_id, errors=(str(exc),))

        jobs = tuple(job for job in queue_state.queue.jobs if job.request.work_id == run.work_id)
        items = tuple(self._item(job) for job in jobs)
        warnings = () if items else ("no provider execution records found",)
        return CampaignExecutionStatusResult(
            campaign_id=campaign_id,
            work_id=run.work_id,
            items=items,
            warnings=warnings,
        )

    @staticmethod
    def _item(job) -> CampaignExecutionItem:
        receipt = job.receipt
        return CampaignExecutionItem(
            request_id=job.request.request_id,
            asset_id=job.request.asset_id,
            media_type=job.request.media_type,
            provider=job.request.provider,
            status=job.status,
            external_id=receipt.external_id if receipt is not None else None,
            outputs=receipt.outputs if receipt is not None else (),
            failure_reason=job.failure_reason,
        )
