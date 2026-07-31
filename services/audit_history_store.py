"""Persist immutable campaign runtime audit history."""

from __future__ import annotations

import fcntl
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.operations_dashboard import AuditEvent, AuditHistory, AuditHistoryService

AUDIT_HISTORY_VERSION = 1


class AuditHistoryStateError(ValueError):
    """Reject corrupt or incompatible audit-history snapshots."""


class JsonAuditHistoryStore:
    """Atomically persist complete runtime audit history."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    def load(self) -> AuditHistory:
        """Load the current history, or an empty history when none exists."""
        with self._locked():
            if not self.path.exists():
                return AuditHistory()
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if payload.get("version") != AUDIT_HISTORY_VERSION:
                    raise AuditHistoryStateError("unsupported audit history version")
                history = AuditHistory(
                    events=tuple(self._event(item) for item in payload["events"])
                )
                self._validate(history)
                return history
            except AuditHistoryStateError:
                raise
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise AuditHistoryStateError("invalid audit history snapshot") from error

    def save(self, history: AuditHistory) -> None:
        """Validate and atomically replace the complete history."""
        self._validate(history)
        with self._locked():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": AUDIT_HISTORY_VERSION,
                "events": [
                    {
                        **asdict(event),
                        "occurred_at": event.occurred_at.isoformat(),
                    }
                    for event in history.events
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

    @staticmethod
    def _event(value: object) -> AuditEvent:
        if not isinstance(value, dict):
            raise TypeError("audit event must be an object")
        return AuditEvent(
            event_id=JsonAuditHistoryStore._string(value["event_id"], "event_id"),
            occurred_at=datetime.fromisoformat(
                JsonAuditHistoryStore._string(value["occurred_at"], "occurred_at")
            ),
            category=JsonAuditHistoryStore._string(value["category"], "category"),
            action=JsonAuditHistoryStore._string(value["action"], "action"),
            subject_id=JsonAuditHistoryStore._string(value["subject_id"], "subject_id"),
            actor=JsonAuditHistoryStore._string(value["actor"], "actor"),
            reference_id=JsonAuditHistoryStore._optional(value.get("reference_id"), "reference_id"),
            detail=JsonAuditHistoryStore._optional(value.get("detail"), "detail"),
        )

    @staticmethod
    def _validate(history: AuditHistory) -> None:
        service = AuditHistoryService()
        validated = AuditHistory()
        try:
            for event in history.events:
                validated = service.record(validated, event)
        except ValueError as error:
            raise AuditHistoryStateError(str(error)) from error

    @staticmethod
    def _string(value: object, field: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field} must be a string")
        return value

    @classmethod
    def _optional(cls, value: object, field: str) -> str | None:
        return None if value is None else cls._string(value, field)
