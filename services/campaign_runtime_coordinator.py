"""Advance one campaign runtime action while preserving human review gates."""

from dataclasses import dataclass
from datetime import datetime

from services.campaign_orchestration import (
    CampaignOrchestrationService,
    CampaignRun,
    WorkflowEvidence,
)
from services.campaign_queue import ExecutionQueue
from services.campaign_run_state import CampaignRunStore
from services.operations_dashboard import AuditHistory
from services.provider_execution import ProviderExecutionAdapter
from services.queue_worker import QueueWorkerService


@dataclass(frozen=True, slots=True)
class CampaignRuntimeResult:
    """Immutable outcome from coordinating at most one campaign action."""

    run: CampaignRun
    queue: ExecutionQueue
    history: AuditHistory
    action: str
    request_id: str | None = None

    @property
    def paused(self) -> bool:
        """Return whether the campaign still requires external or human input."""
        return self.action.startswith("awaiting-") or self.action in {
            "execution-failed",
            "completed",
        }


class CampaignRuntimeCoordinator:
    """Coordinate existing services without bypassing approval or evidence gates."""

    def advance(
        self,
        campaign_id: str,
        store: CampaignRunStore,
        queue: ExecutionQueue,
        history: AuditHistory,
        adapters: tuple[ProviderExecutionAdapter, ...],
        *,
        worker_id: str,
        now: datetime,
        evidence: WorkflowEvidence | None = None,
        max_attempts: int = 1,
    ) -> CampaignRuntimeResult:
        """Perform at most one eligible action for a persisted campaign run."""
        campaign_id = self._required(campaign_id, "campaign_id")
        run = store.load(campaign_id)
        if run.campaign_id != campaign_id:
            raise ValueError("loaded campaign does not match campaign_id")

        if run.stage == "planned":
            self._reject_evidence(evidence, run.stage)
            advanced = CampaignOrchestrationService().advance(run, "in-production")
            store.save(advanced)
            return CampaignRuntimeResult(
                run=advanced,
                queue=queue,
                history=history,
                action="production-started",
            )

        if run.stage == "in-production":
            if evidence is not None:
                if self._has_open_work(queue, run.work_id):
                    return CampaignRuntimeResult(
                        run=run,
                        queue=queue,
                        history=history,
                        action="awaiting-production",
                    )
                advanced = CampaignOrchestrationService().advance(
                    run,
                    "ready",
                    evidence=evidence,
                )
                store.save(advanced)
                return CampaignRuntimeResult(
                    run=advanced,
                    queue=queue,
                    history=history,
                    action="awaiting-publication",
                )
            return self._execute_one(
                run,
                queue,
                history,
                adapters,
                worker_id=worker_id,
                now=now,
                max_attempts=max_attempts,
            )

        if run.stage == "ready":
            if evidence is None:
                return self._paused(run, queue, history, "awaiting-publication")
            advanced = CampaignOrchestrationService().advance(
                run,
                "published",
                evidence=evidence,
            )
            store.save(advanced)
            return self._paused(advanced, queue, history, "awaiting-measurement")

        if run.stage == "published":
            if evidence is None:
                return self._paused(run, queue, history, "awaiting-measurement")
            advanced = CampaignOrchestrationService().advance(
                run,
                "measured",
                evidence=evidence,
            )
            store.save(advanced)
            return CampaignRuntimeResult(
                run=advanced,
                queue=queue,
                history=history,
                action="measurement-recorded",
            )

        if run.stage == "measured":
            self._reject_evidence(evidence, run.stage)
            advanced = CampaignOrchestrationService().advance(run, "completed")
            store.save(advanced)
            return self._paused(advanced, queue, history, "completed")

        if run.stage == "completed":
            self._reject_evidence(evidence, run.stage)
            return self._paused(run, queue, history, "completed")

        raise ValueError(f"unsupported campaign stage: {run.stage}")

    def _execute_one(
        self,
        run: CampaignRun,
        queue: ExecutionQueue,
        history: AuditHistory,
        adapters: tuple[ProviderExecutionAdapter, ...],
        *,
        worker_id: str,
        now: datetime,
        max_attempts: int,
    ) -> CampaignRuntimeResult:
        campaign_jobs = tuple(job for job in queue.jobs if job.request.work_id == run.work_id)
        campaign_queue = ExecutionQueue(jobs=campaign_jobs)
        worker_result = QueueWorkerService().run_next(
            campaign_queue,
            history,
            adapters,
            worker_id=worker_id,
            now=now,
            max_attempts=max_attempts,
        )
        if worker_result.request_id is None:
            return self._paused(run, queue, history, "awaiting-approved-assets")

        merged_queue = self._merge(queue, worker_result.queue)
        job = next(
            item
            for item in worker_result.queue.jobs
            if item.request.request_id == worker_result.request_id
        )
        action = "execution-completed" if job.status == "completed" else "execution-failed"
        return CampaignRuntimeResult(
            run=run,
            queue=merged_queue,
            history=worker_result.history,
            action=action,
            request_id=worker_result.request_id,
        )

    @staticmethod
    def _merge(original: ExecutionQueue, campaign_queue: ExecutionQueue) -> ExecutionQueue:
        replacements = {job.request.request_id: job for job in campaign_queue.jobs}
        return ExecutionQueue(
            jobs=tuple(replacements.get(job.request.request_id, job) for job in original.jobs)
        )

    @staticmethod
    def _has_open_work(queue: ExecutionQueue, work_id: str) -> bool:
        return any(
            job.request.work_id == work_id and job.status in {"scheduled", "claimed"}
            for job in queue.jobs
        )

    @staticmethod
    def _paused(
        run: CampaignRun,
        queue: ExecutionQueue,
        history: AuditHistory,
        action: str,
    ) -> CampaignRuntimeResult:
        return CampaignRuntimeResult(
            run=run,
            queue=queue,
            history=history,
            action=action,
        )

    @staticmethod
    def _reject_evidence(evidence: WorkflowEvidence | None, stage: str) -> None:
        if evidence is not None:
            raise ValueError(f"{stage} stage does not accept evidence")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
