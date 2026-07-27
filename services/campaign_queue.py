"""Schedule approved provider work through an immutable execution queue."""

from dataclasses import dataclass, replace
from datetime import datetime

from services.provider_execution import (
    ExecutionApproval,
    ExecutionReceipt,
    ExecutionRequest,
)

TERMINAL_STATUSES = ("completed", "failed", "cancelled")


@dataclass(frozen=True, slots=True)
class QueueJob:
    """One approved execution request and its queue lifecycle."""

    request: ExecutionRequest
    approval: ExecutionApproval
    scheduled_for: datetime
    priority: int
    status: str = "scheduled"
    claimed_by: str | None = None
    receipt: ExecutionReceipt | None = None
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionQueue:
    """Immutable collection of scheduled execution jobs."""

    jobs: tuple[QueueJob, ...] = ()


class CampaignQueueService:
    """Guard scheduling and queue transitions without executing provider work."""

    def schedule(
        self,
        queue: ExecutionQueue,
        request: ExecutionRequest,
        approval: ExecutionApproval,
        *,
        scheduled_for: datetime,
        priority: int = 0,
    ) -> ExecutionQueue:
        """Add one approved request unless its identity is already queued."""
        request = self._request(request)
        approval = self._approval(request, approval)
        scheduled_for = self._timestamp(scheduled_for, "scheduled_for")
        if priority < 0:
            raise ValueError("priority must be non-negative")
        if any(job.request.request_id == request.request_id for job in queue.jobs):
            raise ValueError(f"request already queued: {request.request_id}")

        job = QueueJob(
            request=request,
            approval=approval,
            scheduled_for=scheduled_for,
            priority=priority,
        )
        return ExecutionQueue(jobs=(*queue.jobs, job))

    def ready(self, queue: ExecutionQueue, *, now: datetime) -> tuple[QueueJob, ...]:
        """Return due, unclaimed work in deterministic execution order."""
        now = self._timestamp(now, "now")
        ready = (
            job for job in queue.jobs if job.status == "scheduled" and job.scheduled_for <= now
        )
        return tuple(
            sorted(
                ready,
                key=lambda job: (
                    -job.priority,
                    job.scheduled_for,
                    job.request.request_id,
                ),
            )
        )

    def claim(
        self,
        queue: ExecutionQueue,
        request_id: str,
        *,
        worker_id: str,
        now: datetime,
    ) -> ExecutionQueue:
        """Claim one due request without executing it."""
        request_id = self._required(request_id, "request_id")
        worker_id = self._required(worker_id, "worker_id")
        now = self._timestamp(now, "now")
        job = self._find(queue, request_id)
        if job.status != "scheduled":
            raise ValueError(f"request cannot be claimed from status: {job.status}")
        if job.scheduled_for > now:
            raise ValueError("request is not ready")
        return self._replace(
            queue,
            request_id,
            replace(job, status="claimed", claimed_by=worker_id),
        )

    def complete(
        self,
        queue: ExecutionQueue,
        request_id: str,
        receipt: ExecutionReceipt,
    ) -> ExecutionQueue:
        """Complete a claimed request with matching execution evidence."""
        request_id = self._required(request_id, "request_id")
        job = self._find(queue, request_id)
        if job.status != "claimed":
            raise ValueError(f"request cannot complete from status: {job.status}")
        self._receipt(job.request, receipt)
        return self._replace(queue, request_id, replace(job, status="completed", receipt=receipt))

    def fail(
        self,
        queue: ExecutionQueue,
        request_id: str,
        *,
        reason: str,
    ) -> ExecutionQueue:
        """Record a claimed request as failed without silently retrying it."""
        request_id = self._required(request_id, "request_id")
        reason = self._required(reason, "failure reason")
        job = self._find(queue, request_id)
        if job.status != "claimed":
            raise ValueError(f"request cannot fail from status: {job.status}")
        return self._replace(
            queue,
            request_id,
            replace(job, status="failed", failure_reason=reason),
        )

    def cancel(self, queue: ExecutionQueue, request_id: str) -> ExecutionQueue:
        """Cancel scheduled work before a worker claims it."""
        request_id = self._required(request_id, "request_id")
        job = self._find(queue, request_id)
        if job.status != "scheduled":
            raise ValueError(f"request cannot be cancelled from status: {job.status}")
        return self._replace(queue, request_id, replace(job, status="cancelled"))

    @classmethod
    def _request(cls, request: ExecutionRequest) -> ExecutionRequest:
        request_id = cls._required(request.request_id, "request_id")
        asset_id = cls._required(request.asset_id, "asset_id")
        work_id = cls._required(request.work_id, "work_id")
        media_type = cls._required(request.media_type, "media_type").casefold()
        provider = cls._required(request.provider, "provider").casefold()
        prompt = cls._required(request.prompt, "prompt")
        if media_type not in ("image", "video"):
            raise ValueError(f"unsupported media_type: {media_type}")
        return replace(
            request,
            request_id=request_id,
            asset_id=asset_id,
            work_id=work_id,
            media_type=media_type,
            provider=provider,
            prompt=prompt,
        )

    @classmethod
    def _approval(
        cls,
        request: ExecutionRequest,
        approval: ExecutionApproval,
    ) -> ExecutionApproval:
        normalized = ExecutionApproval(
            asset_id=cls._required(approval.asset_id, "approval asset_id"),
            media_type=cls._required(approval.media_type, "approval media_type").casefold(),
            provider=cls._required(approval.provider, "approval provider").casefold(),
            approved_by=cls._required(approval.approved_by, "approved_by"),
        )
        if (
            normalized.asset_id != request.asset_id
            or normalized.media_type != request.media_type
            or normalized.provider != request.provider
        ):
            raise PermissionError("approval does not match execution request")
        return normalized

    @classmethod
    def _receipt(cls, request: ExecutionRequest, receipt: ExecutionReceipt) -> None:
        if (
            cls._required(receipt.request_id, "receipt request_id") != request.request_id
            or cls._required(receipt.asset_id, "receipt asset_id") != request.asset_id
            or cls._required(receipt.media_type, "receipt media_type").casefold()
            != request.media_type
            or cls._required(receipt.provider, "receipt provider").casefold() != request.provider
        ):
            raise ValueError("execution receipt does not match queued request")
        cls._required(receipt.external_id, "receipt external_id")

    @staticmethod
    def _timestamp(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone")
        return value

    @staticmethod
    def _find(queue: ExecutionQueue, request_id: str) -> QueueJob:
        for job in queue.jobs:
            if job.request.request_id == request_id:
                return job
        raise KeyError(f"queued request not found: {request_id}")

    @staticmethod
    def _replace(
        queue: ExecutionQueue,
        request_id: str,
        replacement: QueueJob,
    ) -> ExecutionQueue:
        return ExecutionQueue(
            jobs=tuple(
                replacement if job.request.request_id == request_id else job for job in queue.jobs
            )
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
