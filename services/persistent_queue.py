"""Persist execution queues and coordinate expiring worker leases."""

from __future__ import annotations

import fcntl
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from services.campaign_queue import CampaignQueueService, ExecutionQueue, QueueJob
from services.provider_execution import (
    ExecutionApproval,
    ExecutionParameter,
    ExecutionReceipt,
    ExecutionRequest,
)

SNAPSHOT_VERSION = 1


class QueueStateError(ValueError):
    """Reject corrupt snapshots or unsafe lease transitions."""


@dataclass(frozen=True, slots=True)
class WorkerLease:
    """Exclusive, expiring ownership of one queued request."""

    lease_id: str
    request_id: str
    worker_id: str
    acquired_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PersistentQueue:
    """Durable queue state plus currently active worker leases."""

    queue: ExecutionQueue = ExecutionQueue()
    leases: tuple[WorkerLease, ...] = ()


@dataclass(frozen=True, slots=True)
class LeasedQueue:
    """Snapshot handed to one worker together with its fencing lease."""

    state: PersistentQueue
    lease: WorkerLease


class JsonExecutionQueueStore:
    """Atomically save queues and serialize lease acquisition across workers."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    def load(self) -> PersistentQueue:
        """Restore and validate the current versioned queue snapshot."""
        with self._locked():
            return self._load_unlocked()

    def save(self, state: PersistentQueue) -> None:
        """Atomically replace the queue snapshot after complete validation."""
        self._validate(state)
        with self._locked():
            self._write_unlocked(state)

    def lease_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_for: timedelta,
        lease_id: str | None = None,
    ) -> LeasedQueue | None:
        """Reserve the next due unleased job in one locked transaction."""
        worker_id = self._required(worker_id, "worker_id")
        now = self._timestamp(now, "now")
        if lease_for <= timedelta(0):
            raise ValueError("lease_for must be positive")
        lease_id = self._required(lease_id or str(uuid4()), "lease_id")

        with self._locked():
            state = self._without_expired(self._load_unlocked(), now)
            leased_ids = {lease.request_id for lease in state.leases}
            job = next(
                (
                    item
                    for item in CampaignQueueService().ready(state.queue, now=now)
                    if item.request.request_id not in leased_ids
                ),
                None,
            )
            if job is None:
                self._write_unlocked(state)
                return None

            lease = WorkerLease(
                lease_id=lease_id,
                request_id=job.request.request_id,
                worker_id=worker_id,
                acquired_at=now,
                expires_at=now + lease_for,
            )
            updated = PersistentQueue(
                queue=state.queue,
                leases=(*state.leases, lease),
            )
            self._write_unlocked(updated)
            return LeasedQueue(state=updated, lease=lease)

    def renew(
        self,
        lease: WorkerLease,
        *,
        now: datetime,
        lease_for: timedelta,
    ) -> WorkerLease:
        """Extend a matching active lease without changing queue work."""
        now = self._timestamp(now, "now")
        if lease_for <= timedelta(0):
            raise ValueError("lease_for must be positive")

        with self._locked():
            state = self._without_expired(self._load_unlocked(), now)
            current = self._matching_lease(state, lease)
            renewed = WorkerLease(
                lease_id=current.lease_id,
                request_id=current.request_id,
                worker_id=current.worker_id,
                acquired_at=current.acquired_at,
                expires_at=now + lease_for,
            )
            updated = PersistentQueue(
                queue=state.queue,
                leases=tuple(
                    renewed if item.lease_id == current.lease_id else item
                    for item in state.leases
                ),
            )
            self._write_unlocked(updated)
            return renewed

    def commit(
        self,
        lease: WorkerLease,
        result: ExecutionQueue,
        *,
        now: datetime,
    ) -> PersistentQueue:
        """Persist one terminal worker result only with its active fencing lease."""
        now = self._timestamp(now, "now")
        with self._locked():
            state = self._without_expired(self._load_unlocked(), now)
            current = self._matching_lease(state, lease)
            updated_queue = self._merge_result(state.queue, result, current.request_id)
            updated = PersistentQueue(
                queue=updated_queue,
                leases=tuple(
                    item for item in state.leases if item.lease_id != current.lease_id
                ),
            )
            self._write_unlocked(updated)
            return updated

    def release(
        self,
        lease: WorkerLease,
        *,
        now: datetime,
    ) -> PersistentQueue:
        """Release active work without changing its queued state."""
        now = self._timestamp(now, "now")
        with self._locked():
            state = self._without_expired(self._load_unlocked(), now)
            current = self._matching_lease(state, lease)
            updated = PersistentQueue(
                queue=state.queue,
                leases=tuple(
                    item for item in state.leases if item.lease_id != current.lease_id
                ),
            )
            self._write_unlocked(updated)
            return updated

    def _load_unlocked(self) -> PersistentQueue:
        if not self.path.exists():
            return PersistentQueue()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if value.get("version") != SNAPSHOT_VERSION:
                raise QueueStateError("unsupported queue snapshot version")
            state = PersistentQueue(
                queue=ExecutionQueue(
                    jobs=tuple(self._job(item) for item in self._objects(value["jobs"], "jobs"))
                ),
                leases=tuple(
                    self._lease(item) for item in self._objects(value["leases"], "leases")
                ),
            )
            self._validate(state)
            return state
        except QueueStateError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise QueueStateError("invalid queue snapshot") from error

    def _write_unlocked(self, state: PersistentQueue) -> None:
        self._validate(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": SNAPSHOT_VERSION,
            "jobs": [self._job_value(job) for job in state.queue.jobs],
            "leases": [self._lease_value(lease) for lease in state.leases],
        }
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            delete=False,
        ) as temporary:
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.path)

    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")

        class Lock:
            def __enter__(self):
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                return handle

            def __exit__(self, exc_type, exc, traceback):
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
                return False

        return Lock()

    @classmethod
    def _validate(cls, state: PersistentQueue) -> None:
        request_ids = tuple(job.request.request_id for job in state.queue.jobs)
        if len(request_ids) != len(set(request_ids)):
            raise QueueStateError("queue request IDs must be unique")
        lease_ids = tuple(lease.lease_id for lease in state.leases)
        if len(lease_ids) != len(set(lease_ids)):
            raise QueueStateError("worker lease IDs must be unique")
        leased_requests = tuple(lease.request_id for lease in state.leases)
        if len(leased_requests) != len(set(leased_requests)):
            raise QueueStateError("a request may have only one worker lease")
        known = set(request_ids)
        for lease in state.leases:
            cls._required(lease.lease_id, "lease_id")
            cls._required(lease.worker_id, "worker_id")
            if lease.request_id not in known:
                raise QueueStateError("worker lease references unknown request")
            cls._timestamp(lease.acquired_at, "acquired_at")
            cls._timestamp(lease.expires_at, "expires_at")
            if lease.expires_at <= lease.acquired_at:
                raise QueueStateError("worker lease expiry must follow acquisition")
            job = cls._find(state.queue, lease.request_id)
            if job.status != "scheduled":
                raise QueueStateError("only scheduled work may hold a worker lease")

    @staticmethod
    def _without_expired(state: PersistentQueue, now: datetime) -> PersistentQueue:
        return PersistentQueue(
            queue=state.queue,
            leases=tuple(lease for lease in state.leases if lease.expires_at > now),
        )

    @classmethod
    def _matching_lease(
        cls,
        state: PersistentQueue,
        supplied: WorkerLease,
    ) -> WorkerLease:
        for current in state.leases:
            if current.lease_id == supplied.lease_id:
                if (
                    current.request_id != supplied.request_id
                    or current.worker_id != supplied.worker_id
                ):
                    raise PermissionError("worker lease identity does not match")
                return current
        raise PermissionError("worker lease is missing or expired")

    @classmethod
    def _merge_result(
        cls,
        stored: ExecutionQueue,
        result: ExecutionQueue,
        request_id: str,
    ) -> ExecutionQueue:
        if tuple(job.request.request_id for job in stored.jobs) != tuple(
            job.request.request_id for job in result.jobs
        ):
            raise QueueStateError("worker result changed queue identities or order")
        stored_by_id = {job.request.request_id: job for job in stored.jobs}
        result_job = cls._find(result, request_id)
        if result_job.status not in ("completed", "failed"):
            raise QueueStateError("leased worker result must be completed or failed")
        for job in result.jobs:
            if job.request.request_id != request_id and job != stored_by_id[job.request.request_id]:
                raise QueueStateError("worker result changed an unleased request")
        return result

    @staticmethod
    def _find(queue: ExecutionQueue, request_id: str) -> QueueJob:
        for job in queue.jobs:
            if job.request.request_id == request_id:
                return job
        raise QueueStateError(f"queued request not found: {request_id}")

    @classmethod
    def _job(cls, value: dict[str, object]) -> QueueJob:
        request = cls._object(value["request"], "request")
        approval = cls._object(value["approval"], "approval")
        receipt_value = value.get("receipt")
        receipt = (
            cls._receipt(cls._object(receipt_value, "receipt"))
            if receipt_value is not None
            else None
        )
        return QueueJob(
            request=ExecutionRequest(
                request_id=cls._string(request["request_id"], "request_id"),
                asset_id=cls._string(request["asset_id"], "asset_id"),
                work_id=cls._string(request["work_id"], "work_id"),
                media_type=cls._string(request["media_type"], "media_type"),
                provider=cls._string(request["provider"], "provider"),
                prompt=cls._string(request["prompt"], "prompt"),
                parameters=tuple(
                    ExecutionParameter(
                        name=cls._string(item["name"], "parameter.name"),
                        value=cls._string(item["value"], "parameter.value"),
                    )
                    for item in cls._objects(request["parameters"], "parameters")
                ),
            ),
            approval=ExecutionApproval(
                asset_id=cls._string(approval["asset_id"], "approval.asset_id"),
                media_type=cls._string(approval["media_type"], "approval.media_type"),
                provider=cls._string(approval["provider"], "approval.provider"),
                approved_by=cls._string(approval["approved_by"], "approved_by"),
            ),
            scheduled_for=cls._date(value["scheduled_for"], "scheduled_for"),
            priority=cls._integer(value["priority"], "priority"),
            status=cls._string(value["status"], "status"),
            claimed_by=cls._optional_string(value.get("claimed_by"), "claimed_by"),
            receipt=receipt,
            failure_reason=cls._optional_string(
                value.get("failure_reason"), "failure_reason"
            ),
        )

    @staticmethod
    def _job_value(job: QueueJob) -> dict[str, object]:
        value = asdict(job)
        value["scheduled_for"] = job.scheduled_for.isoformat()
        return value

    @classmethod
    def _receipt(cls, value: dict[str, object]) -> ExecutionReceipt:
        return ExecutionReceipt(
            request_id=cls._string(value["request_id"], "receipt.request_id"),
            asset_id=cls._string(value["asset_id"], "receipt.asset_id"),
            media_type=cls._string(value["media_type"], "receipt.media_type"),
            provider=cls._string(value["provider"], "receipt.provider"),
            external_id=cls._string(value["external_id"], "receipt.external_id"),
            outputs=tuple(cls._strings(value["outputs"], "receipt.outputs")),
        )

    @classmethod
    def _lease(cls, value: dict[str, object]) -> WorkerLease:
        return WorkerLease(
            lease_id=cls._string(value["lease_id"], "lease_id"),
            request_id=cls._string(value["request_id"], "request_id"),
            worker_id=cls._string(value["worker_id"], "worker_id"),
            acquired_at=cls._date(value["acquired_at"], "acquired_at"),
            expires_at=cls._date(value["expires_at"], "expires_at"),
        )

    @staticmethod
    def _lease_value(lease: WorkerLease) -> dict[str, str]:
        return {
            "lease_id": lease.lease_id,
            "request_id": lease.request_id,
            "worker_id": lease.worker_id,
            "acquired_at": lease.acquired_at.isoformat(),
            "expires_at": lease.expires_at.isoformat(),
        }

    @staticmethod
    def _object(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise TypeError(f"{field} must be an object")
        return value

    @classmethod
    def _objects(cls, value: object, field: str) -> tuple[dict[str, object], ...]:
        if not isinstance(value, list):
            raise TypeError(f"{field} must be a list")
        return tuple(cls._object(item, field) for item in value)

    @staticmethod
    def _string(value: object, field: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field} must be a string")
        return value

    @classmethod
    def _optional_string(cls, value: object, field: str) -> str | None:
        if value is None:
            return None
        return cls._string(value, field)

    @classmethod
    def _strings(cls, value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise TypeError(f"{field} must be a list")
        return tuple(cls._string(item, field) for item in value)

    @staticmethod
    def _integer(value: object, field: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{field} must be an integer")
        return value

    @classmethod
    def _date(cls, value: object, field: str) -> datetime:
        return cls._timestamp(datetime.fromisoformat(cls._string(value, field)), field)

    @staticmethod
    def _timestamp(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone")
        return value

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
