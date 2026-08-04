"""Structured API for campaign execution tasks."""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.project import Project
from services.campaign import slugify
from services.campaign_queue import QueueJob
from services.persistent_queue import JsonExecutionQueueStore, QueueStateError

QUEUE_PATH = Path(".creativeos") / "runtime" / "execution-queue.json"


@dataclass(frozen=True, slots=True)
class CampaignTask:
    """One campaign execution job exposed as a read-only task."""

    request_id: str
    asset_id: str
    media_type: str
    provider: str
    scheduled_for: datetime
    status: str
    priority: int


@dataclass(frozen=True, slots=True)
class CampaignTasksResult:
    """Structured task summary for one campaign and reference date."""

    campaign: str
    today: date
    overdue: tuple[CampaignTask, ...] = ()
    due_today: tuple[CampaignTask, ...] = ()
    upcoming: tuple[CampaignTask, ...] = ()
    completed: tuple[CampaignTask, ...] = ()
    completion_percent: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether tasks were loaded without errors."""
        return not self.errors


class CampaignTasksAPI:
    """Read and classify queued campaign execution work."""

    def __init__(
        self,
        project: Project,
        store: JsonExecutionQueueStore | None = None,
    ) -> None:
        self.project = project
        self.store = store or JsonExecutionQueueStore(project.root / QUEUE_PATH)

    def today(
        self,
        campaign_name: str,
        *,
        today: date | None = None,
    ) -> CampaignTasksResult:
        """Return overdue, current, upcoming, and completed campaign tasks."""
        reference_date = today or date.today()
        campaign_slug = slugify(campaign_name)
        campaign_path = self.project.campaigns_path / campaign_slug

        if not campaign_path.is_dir():
            return CampaignTasksResult(
                campaign=campaign_name,
                today=reference_date,
                errors=(
                    f'Campaign workspace not found for "{campaign_name}". '
                    f'Run: creativeos campaign create "{campaign_name}"',
                ),
            )

        try:
            state = self.store.load()
        except QueueStateError as exc:
            return CampaignTasksResult(
                campaign=campaign_name,
                today=reference_date,
                errors=(f"Invalid execution queue: {exc}",),
            )

        jobs = tuple(
            job for job in state.queue.jobs if slugify(job.request.work_id) == campaign_slug
        )
        active = tuple(job for job in jobs if job.status in ("scheduled", "claimed"))
        completed_jobs = tuple(job for job in jobs if job.status == "completed")
        warnings = tuple(
            f"Task {job.request.request_id} is {job.status}"
            for job in jobs
            if job.status in ("failed", "cancelled")
        )

        overdue = self._sorted(job for job in active if job.scheduled_for.date() < reference_date)
        due_today = self._sorted(
            job for job in active if job.scheduled_for.date() == reference_date
        )
        upcoming = self._sorted(job for job in active if job.scheduled_for.date() > reference_date)
        completed = self._sorted(completed_jobs)
        completion_percent = round(len(completed_jobs) / len(jobs) * 100) if jobs else 0

        return CampaignTasksResult(
            campaign=campaign_name,
            today=reference_date,
            overdue=tuple(self._task(job) for job in overdue),
            due_today=tuple(self._task(job) for job in due_today),
            upcoming=tuple(self._task(job) for job in upcoming),
            completed=tuple(self._task(job) for job in completed),
            completion_percent=completion_percent,
            warnings=warnings,
        )

    @staticmethod
    def _sorted(jobs) -> tuple[QueueJob, ...]:
        return tuple(
            sorted(
                jobs,
                key=lambda job: (
                    job.scheduled_for,
                    -job.priority,
                    job.request.request_id,
                ),
            )
        )

    @staticmethod
    def _task(job: QueueJob) -> CampaignTask:
        return CampaignTask(
            request_id=job.request.request_id,
            asset_id=job.request.asset_id,
            media_type=job.request.media_type,
            provider=job.request.provider,
            scheduled_for=job.scheduled_for,
            status=job.status,
            priority=job.priority,
        )
