"""Persist deterministic checkpoints around state-changing campaign runtime actions."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.campaign_orchestration import CampaignRun, WorkflowEvidence
from services.campaign_queue import CampaignQueueService, ExecutionQueue
from services.campaign_run_state import CampaignRunStore
from services.campaign_runtime_coordinator import (
    CampaignRuntimeCoordinator,
    CampaignRuntimeResult,
)
from services.operations_dashboard import AuditHistory
from services.provider_execution import ProviderExecutionAdapter

CHECKPOINT_VERSION = 1


class RuntimeCheckpointError(ValueError):
    """Reject corrupt snapshots or unsafe checkpoint transitions."""


@dataclass(frozen=True, slots=True)
class RuntimeCheckpoint:
    """Durable identity and outcome of one state-changing runtime action."""

    checkpoint_id: str
    campaign_id: str
    action_key: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    result_action: str | None = None
    request_id: str | None = None
    resulting_stage: str | None = None


@dataclass(frozen=True, slots=True)
class CheckpointedRuntimeResult:
    """Runtime result plus its durable recovery state, when one was needed."""

    checkpoint: RuntimeCheckpoint | None
    result: CampaignRuntimeResult | None
    replayed: bool = False

    @property
    def uncertain(self) -> bool:
        """Return whether manual reconciliation is required before any retry."""
        return self.checkpoint is not None and self.checkpoint.status == "uncertain"


class JsonRuntimeCheckpointStore:
    """Atomically persist checkpoint claims and terminal outcomes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    def load(self) -> tuple[RuntimeCheckpoint, ...]:
        """Restore every checkpoint in deterministic insertion order."""
        with self._locked():
            return self._load_unlocked()

    def recover_unfinished(self, campaign_id: str) -> RuntimeCheckpoint | None:
        """Fence any prior started or uncertain action before new campaign work."""
        campaign_id = self._required(campaign_id, "campaign_id")
        with self._locked():
            checkpoints = self._load_unlocked()
            unfinished = next(
                (
                    item
                    for item in checkpoints
                    if item.campaign_id == campaign_id and item.status in {"started", "uncertain"}
                ),
                None,
            )
            if unfinished is None or unfinished.status == "uncertain":
                return unfinished
            recovered = replace(unfinished, status="uncertain")
            self._write_unlocked(
                tuple(
                    recovered if item.checkpoint_id == unfinished.checkpoint_id else item
                    for item in checkpoints
                )
            )
            return recovered

    def begin(
        self,
        *,
        campaign_id: str,
        action_key: str,
        now: datetime,
    ) -> tuple[RuntimeCheckpoint, bool]:
        """Claim an action, or recover its existing terminal/uncertain checkpoint."""
        campaign_id = self._required(campaign_id, "campaign_id")
        action_key = self._required(action_key, "action_key")
        now = self._timestamp(now, "now")
        checkpoint_id = self._identity(campaign_id, action_key)

        with self._locked():
            checkpoints = self._load_unlocked()
            existing = next(
                (item for item in checkpoints if item.checkpoint_id == checkpoint_id),
                None,
            )
            if existing is not None:
                if existing.status == "started":
                    existing = replace(existing, status="uncertain")
                    checkpoints = tuple(
                        existing if item.checkpoint_id == checkpoint_id else item
                        for item in checkpoints
                    )
                    self._write_unlocked(checkpoints)
                return existing, False

            checkpoint = RuntimeCheckpoint(
                checkpoint_id=checkpoint_id,
                campaign_id=campaign_id,
                action_key=action_key,
                status="started",
                started_at=now,
            )
            self._write_unlocked((*checkpoints, checkpoint))
            return checkpoint, True

    def complete(
        self,
        checkpoint: RuntimeCheckpoint,
        result: CampaignRuntimeResult,
        *,
        now: datetime,
    ) -> RuntimeCheckpoint:
        """Record the known result of the matching started checkpoint."""
        return self._finish(
            checkpoint,
            status="completed",
            now=now,
            result=result,
        )

    def mark_uncertain(
        self,
        checkpoint: RuntimeCheckpoint,
        *,
        now: datetime,
    ) -> RuntimeCheckpoint:
        """Fence an action whose provider or persistence outcome is unknown."""
        return self._finish(checkpoint, status="uncertain", now=now)

    def _finish(
        self,
        checkpoint: RuntimeCheckpoint,
        *,
        status: str,
        now: datetime,
        result: CampaignRuntimeResult | None = None,
    ) -> RuntimeCheckpoint:
        now = self._timestamp(now, "now")
        with self._locked():
            checkpoints = self._load_unlocked()
            current = next(
                (item for item in checkpoints if item.checkpoint_id == checkpoint.checkpoint_id),
                None,
            )
            if current != checkpoint or current.status != "started":
                raise RuntimeCheckpointError("checkpoint is not the active started action")
            updated = replace(
                current,
                status=status,
                completed_at=now if status == "completed" else None,
                result_action=result.action if result is not None else None,
                request_id=result.request_id if result is not None else None,
                resulting_stage=result.run.stage if result is not None else None,
            )
            self._write_unlocked(
                tuple(
                    updated if item.checkpoint_id == current.checkpoint_id else item
                    for item in checkpoints
                )
            )
            return updated

    def _load_unlocked(self) -> tuple[RuntimeCheckpoint, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != CHECKPOINT_VERSION:
                raise RuntimeCheckpointError("unsupported runtime checkpoint version")
            checkpoints = tuple(self._checkpoint(item) for item in payload["checkpoints"])
            self._validate(checkpoints)
            return checkpoints
        except RuntimeCheckpointError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeCheckpointError("invalid runtime checkpoint snapshot") from error

    def _write_unlocked(self, checkpoints: tuple[RuntimeCheckpoint, ...]) -> None:
        self._validate(checkpoints)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CHECKPOINT_VERSION,
            "checkpoints": [
                {
                    **asdict(item),
                    "started_at": item.started_at.isoformat(),
                    "completed_at": (
                        item.completed_at.isoformat() if item.completed_at is not None else None
                    ),
                }
                for item in checkpoints
            ],
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
    def _checkpoint(cls, value: dict[str, object]) -> RuntimeCheckpoint:
        if not isinstance(value, dict):
            raise RuntimeCheckpointError("checkpoint must be an object")
        completed_at = value.get("completed_at")
        return RuntimeCheckpoint(
            checkpoint_id=cls._required(value["checkpoint_id"], "checkpoint_id"),
            campaign_id=cls._required(value["campaign_id"], "campaign_id"),
            action_key=cls._required(value["action_key"], "action_key"),
            status=cls._required(value["status"], "status"),
            started_at=datetime.fromisoformat(cls._required(value["started_at"], "started_at")),
            completed_at=(
                datetime.fromisoformat(cls._required(completed_at, "completed_at"))
                if completed_at is not None
                else None
            ),
            result_action=cls._optional(value.get("result_action")),
            request_id=cls._optional(value.get("request_id")),
            resulting_stage=cls._optional(value.get("resulting_stage")),
        )

    @classmethod
    def _validate(cls, checkpoints: tuple[RuntimeCheckpoint, ...]) -> None:
        identities = tuple(item.checkpoint_id for item in checkpoints)
        if len(identities) != len(set(identities)):
            raise RuntimeCheckpointError("checkpoint IDs must be unique")
        for item in checkpoints:
            if item.status not in {"started", "completed", "uncertain"}:
                raise RuntimeCheckpointError(f"unsupported checkpoint status: {item.status}")
            cls._timestamp(item.started_at, "started_at")
            expected = cls._identity(item.campaign_id, item.action_key)
            if item.checkpoint_id != expected:
                raise RuntimeCheckpointError("checkpoint identity does not match its action")
            if item.status == "completed":
                if (
                    item.completed_at is None
                    or item.result_action is None
                    or item.resulting_stage is None
                ):
                    raise RuntimeCheckpointError("completed checkpoint is missing its outcome")
                cls._timestamp(item.completed_at, "completed_at")
            elif any(
                value is not None
                for value in (
                    item.completed_at,
                    item.result_action,
                    item.request_id,
                    item.resulting_stage,
                )
            ):
                raise RuntimeCheckpointError("unfinished checkpoint contains an outcome")

    @staticmethod
    def _identity(campaign_id: str, action_key: str) -> str:
        digest = hashlib.sha256(f"{campaign_id}\0{action_key}".encode()).hexdigest()
        return f"runtime-{digest[:24]}"

    @staticmethod
    def _timestamp(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone")
        return value

    @staticmethod
    def _required(value: object, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must not be empty")
        return value.strip()

    @classmethod
    def _optional(cls, value: object) -> str | None:
        return None if value is None else cls._required(value, "optional value")


class CheckpointedCampaignRuntime:
    """Fence state-changing coordinator calls against replay after restart."""

    _EVIDENCE_BY_STAGE = {
        "in-production": "approved-assets",
        "ready": "publication-receipt",
        "published": "campaign-measurement",
    }

    def advance(
        self,
        campaign_id: str,
        run_store: CampaignRunStore,
        checkpoint_store: JsonRuntimeCheckpointStore,
        queue: ExecutionQueue,
        history: AuditHistory,
        adapters: tuple[ProviderExecutionAdapter, ...],
        *,
        worker_id: str,
        now: datetime,
        evidence: WorkflowEvidence | None = None,
        max_attempts: int = 1,
    ) -> CheckpointedRuntimeResult:
        """Advance once, replay a known outcome, or stop at an uncertain action."""
        unfinished = checkpoint_store.recover_unfinished(campaign_id)
        if unfinished is not None:
            return CheckpointedRuntimeResult(
                checkpoint=unfinished,
                result=None,
                replayed=True,
            )
        run = run_store.load(campaign_id)
        action_key = self._action_key(run, queue, now=now, evidence=evidence)
        if action_key is None:
            result = CampaignRuntimeCoordinator().advance(
                campaign_id,
                run_store,
                queue,
                history,
                adapters,
                worker_id=worker_id,
                now=now,
                evidence=evidence,
                max_attempts=max_attempts,
            )
            return CheckpointedRuntimeResult(checkpoint=None, result=result)

        checkpoint, acquired = checkpoint_store.begin(
            campaign_id=campaign_id,
            action_key=action_key,
            now=now,
        )
        if not acquired:
            return CheckpointedRuntimeResult(
                checkpoint=checkpoint,
                result=None,
                replayed=True,
            )

        try:
            result = CampaignRuntimeCoordinator().advance(
                campaign_id,
                run_store,
                queue,
                history,
                adapters,
                worker_id=worker_id,
                now=now,
                evidence=evidence,
                max_attempts=max_attempts,
            )
        except BaseException:
            checkpoint_store.mark_uncertain(checkpoint, now=now)
            raise

        completed = checkpoint_store.complete(checkpoint, result, now=now)
        return CheckpointedRuntimeResult(checkpoint=completed, result=result)

    @classmethod
    def _action_key(
        cls,
        run: CampaignRun,
        queue: ExecutionQueue,
        *,
        now: datetime,
        evidence: WorkflowEvidence | None,
    ) -> str | None:
        if run.stage == "planned" and evidence is None:
            return "stage:planned"
        if run.stage == "measured" and evidence is None:
            return "stage:measured"

        expected_evidence = cls._EVIDENCE_BY_STAGE.get(run.stage)
        if evidence is not None:
            if evidence.kind != expected_evidence:
                return None
            if run.stage == "in-production" and any(
                job.request.work_id == run.work_id and job.status in {"scheduled", "claimed"}
                for job in queue.jobs
            ):
                return None
            return f"evidence:{run.stage}:{evidence.kind}:{evidence.reference_id}"

        if run.stage != "in-production":
            return None
        campaign_queue = ExecutionQueue(
            jobs=tuple(job for job in queue.jobs if job.request.work_id == run.work_id)
        )
        ready = CampaignQueueService().ready(campaign_queue, now=now)
        if not ready:
            return None
        return f"execution:{ready[0].request.request_id}"
