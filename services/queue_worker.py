"""Execute one approved queue job through a configured provider adapter."""

from dataclasses import dataclass
from datetime import datetime

from services.campaign_queue import CampaignQueueService, ExecutionQueue, QueueJob
from services.operations_dashboard import (
    AuditEvent,
    AuditHistory,
    AuditHistoryService,
)
from services.provider_execution import (
    ProviderExecutionAdapter,
    ProviderExecutionService,
)


class RetryableProviderError(RuntimeError):
    """Signal a transient provider failure that may be attempted again."""


@dataclass(frozen=True, slots=True)
class WorkerAttempt:
    """Evidence for one provider execution attempt."""

    number: int
    succeeded: bool
    detail: str


@dataclass(frozen=True, slots=True)
class WorkerResult:
    """Immutable result of processing at most one ready queue job."""

    queue: ExecutionQueue
    history: AuditHistory
    request_id: str | None
    attempts: tuple[WorkerAttempt, ...] = ()


class QueueWorkerService:
    """Claim and execute ready work while preserving queue and audit evidence."""

    def run_next(
        self,
        queue: ExecutionQueue,
        history: AuditHistory,
        adapters: tuple[ProviderExecutionAdapter, ...],
        *,
        worker_id: str,
        now: datetime,
        max_attempts: int = 1,
    ) -> WorkerResult:
        """Process the next due job without running a background worker loop."""
        worker_id = self._required(worker_id, "worker_id")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        queue_service = CampaignQueueService()
        ready = queue_service.ready(queue, now=now)
        if not ready:
            return WorkerResult(queue=queue, history=history, request_id=None)

        job = ready[0]
        request_id = job.request.request_id
        claimed = queue_service.claim(
            queue,
            request_id,
            worker_id=worker_id,
            now=now,
        )
        history = self._record(
            history,
            request_id,
            now,
            worker_id,
            action="claimed",
            detail=f"provider={job.request.provider}",
        )

        try:
            adapter = self._adapter(job, adapters)
        except ValueError as error:
            return self._failed(
                claimed,
                history,
                job,
                worker_id,
                now,
                (WorkerAttempt(number=1, succeeded=False, detail=str(error)),),
            )

        attempts = []
        for number in range(1, max_attempts + 1):
            try:
                receipt = ProviderExecutionService().execute(
                    job.request,
                    job.approval,
                    adapter,
                )
            except RetryableProviderError as error:
                attempts.append(WorkerAttempt(number=number, succeeded=False, detail=str(error)))
                history = self._record(
                    history,
                    request_id,
                    now,
                    worker_id,
                    action="retryable-failure",
                    reference_id=str(number),
                    detail=str(error),
                )
                if number < max_attempts:
                    continue
                return self._failed(
                    claimed,
                    history,
                    job,
                    worker_id,
                    now,
                    tuple(attempts),
                )
            except Exception as error:
                attempts.append(WorkerAttempt(number=number, succeeded=False, detail=str(error)))
                return self._failed(
                    claimed,
                    history,
                    job,
                    worker_id,
                    now,
                    tuple(attempts),
                )

            attempts.append(
                WorkerAttempt(
                    number=number,
                    succeeded=True,
                    detail=receipt.external_id,
                )
            )
            completed = queue_service.complete(claimed, request_id, receipt)
            history = self._record(
                history,
                request_id,
                now,
                worker_id,
                action="completed",
                reference_id=receipt.external_id,
                detail=f"attempt={number}",
            )
            return WorkerResult(
                queue=completed,
                history=history,
                request_id=request_id,
                attempts=tuple(attempts),
            )

        raise AssertionError("worker attempt loop did not return")

    def _failed(
        self,
        queue: ExecutionQueue,
        history: AuditHistory,
        job: QueueJob,
        worker_id: str,
        now: datetime,
        attempts: tuple[WorkerAttempt, ...],
    ) -> WorkerResult:
        reason = attempts[-1].detail
        failed = CampaignQueueService().fail(
            queue,
            job.request.request_id,
            reason=reason,
        )
        history = self._record(
            history,
            job.request.request_id,
            now,
            worker_id,
            action="failed",
            detail=reason,
        )
        return WorkerResult(
            queue=failed,
            history=history,
            request_id=job.request.request_id,
            attempts=attempts,
        )

    @staticmethod
    def _adapter(
        job: QueueJob,
        adapters: tuple[ProviderExecutionAdapter, ...],
    ) -> ProviderExecutionAdapter:
        matching = tuple(
            adapter
            for adapter in adapters
            if adapter.provider.strip().casefold() == job.request.provider
            and job.request.media_type
            in tuple(item.strip().casefold() for item in adapter.media_types)
        )
        if not matching:
            raise ValueError(
                f"no adapter configured for {job.request.provider}/{job.request.media_type}"
            )
        if len(matching) > 1:
            raise ValueError(
                f"multiple adapters configured for {job.request.provider}/{job.request.media_type}"
            )
        return matching[0]

    @staticmethod
    def _record(
        history: AuditHistory,
        request_id: str,
        occurred_at: datetime,
        actor: str,
        *,
        action: str,
        reference_id: str | None = None,
        detail: str | None = None,
    ) -> AuditHistory:
        event_id = f"{request_id}:{action}"
        if reference_id is not None and action == "retryable-failure":
            event_id = f"{event_id}:{reference_id}"
        return AuditHistoryService().record(
            history,
            AuditEvent(
                event_id=event_id,
                occurred_at=occurred_at,
                category="execution",
                action=action,
                subject_id=request_id,
                actor=actor,
                reference_id=reference_id,
                detail=detail,
            ),
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
