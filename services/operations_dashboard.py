"""Build read-only operations views and immutable audit history."""

from dataclasses import dataclass
from datetime import datetime

from services.campaign_orchestration import CampaignRun
from services.campaign_queue import ExecutionQueue


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """One attributable operational event."""

    event_id: str
    occurred_at: datetime
    category: str
    action: str
    subject_id: str
    actor: str
    reference_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class AuditHistory:
    """Immutable ordered collection of operational events."""

    events: tuple[AuditEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class CampaignStatus:
    """Compact campaign row for operational review."""

    campaign_id: str
    work_id: str
    stage: str
    requires_action: str
    evidence_count: int


@dataclass(frozen=True, slots=True)
class FailedQueueJob:
    """Failed execution work requiring human attention."""

    request_id: str
    asset_id: str
    provider: str
    reason: str


@dataclass(frozen=True, slots=True)
class OperationsDashboard:
    """Deterministic read model for campaigns, queued work, and audit activity."""

    campaigns: tuple[CampaignStatus, ...]
    queue_status_counts: tuple[tuple[str, int], ...]
    failed_jobs: tuple[FailedQueueJob, ...]
    recent_events: tuple[AuditEvent, ...]


class AuditHistoryService:
    """Validate and append audit evidence without changing operational state."""

    _CATEGORIES = (
        "campaign",
        "approval",
        "queue",
        "execution",
        "publishing",
        "measurement",
    )

    def record(self, history: AuditHistory, event: AuditEvent) -> AuditHistory:
        """Append one unique, attributable, timezone-aware event."""
        normalized = AuditEvent(
            event_id=self._required(event.event_id, "event_id"),
            occurred_at=self._timestamp(event.occurred_at),
            category=self._required(event.category, "category").casefold(),
            action=self._required(event.action, "action").casefold(),
            subject_id=self._required(event.subject_id, "subject_id"),
            actor=self._required(event.actor, "actor"),
            reference_id=self._optional(event.reference_id),
            detail=self._optional(event.detail),
        )
        if normalized.category not in self._CATEGORIES:
            raise ValueError(f"unsupported audit category: {normalized.category}")
        if any(item.event_id == normalized.event_id for item in history.events):
            raise ValueError(f"audit event already recorded: {normalized.event_id}")
        return AuditHistory(events=(*history.events, normalized))

    @staticmethod
    def _timestamp(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class OperationsDashboardService:
    """Project existing campaign and queue state without mutating either."""

    def build(
        self,
        runs: tuple[CampaignRun, ...],
        queue: ExecutionQueue,
        history: AuditHistory,
        *,
        recent_event_limit: int = 20,
    ) -> OperationsDashboard:
        """Return a deterministic operational snapshot."""
        if recent_event_limit < 0:
            raise ValueError("recent_event_limit must be non-negative")

        campaign_ids = tuple(run.campaign_id for run in runs)
        if len(campaign_ids) != len(set(campaign_ids)):
            raise ValueError("campaign IDs must be unique")

        request_ids = tuple(job.request.request_id for job in queue.jobs)
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("queue request IDs must be unique")

        campaigns = tuple(
            sorted(
                (
                    CampaignStatus(
                        campaign_id=run.campaign_id,
                        work_id=run.work_id,
                        stage=run.stage,
                        requires_action=run.requires_action,
                        evidence_count=len(run.evidence),
                    )
                    for run in runs
                ),
                key=lambda item: item.campaign_id,
            )
        )

        counts: dict[str, int] = {}
        failures = []
        for job in queue.jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
            if job.status == "failed":
                reason = (job.failure_reason or "").strip()
                if not reason:
                    raise ValueError(
                        f"failed queue job has no failure reason: {job.request.request_id}"
                    )
                failures.append(
                    FailedQueueJob(
                        request_id=job.request.request_id,
                        asset_id=job.request.asset_id,
                        provider=job.request.provider,
                        reason=reason,
                    )
                )

        ordered_events = sorted(
            history.events,
            key=lambda item: (item.occurred_at, item.event_id),
            reverse=True,
        )
        recent_events = tuple(ordered_events[:recent_event_limit])
        return OperationsDashboard(
            campaigns=campaigns,
            queue_status_counts=tuple(sorted(counts.items())),
            failed_jobs=tuple(sorted(failures, key=lambda item: item.request_id)),
            recent_events=recent_events,
        )
