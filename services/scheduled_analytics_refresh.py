"""Run durable, read-only analytics refreshes without duplicate collection."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from services.instagram_analytics_connector import InstagramPublication
from services.performance_ingestion import PerformanceDataset

REFRESH_STORE_VERSION = 1
REFRESH_STATUSES = {"started", "completed", "failed", "uncertain"}


class ScheduledAnalyticsRefreshError(ValueError):
    """Reject invalid schedules, snapshots, or unsafe refresh transitions."""


@dataclass(frozen=True, slots=True)
class AnalyticsRefreshSchedule:
    """Recurring read-only analytics collection configuration."""

    schedule_id: str
    publications: tuple[InstagramPublication, ...]
    interval: timedelta
    starts_at: datetime


@dataclass(frozen=True, slots=True)
class AnalyticsRefreshAttempt:
    """Durable state and outcome for one scheduled refresh window."""

    attempt_id: str
    schedule_id: str
    window_started_at: datetime
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    record_count: int | None = None
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ScheduledAnalyticsRefreshResult:
    """Refresh attempt together with newly collected observations, if any."""

    attempt: AnalyticsRefreshAttempt | None
    dataset: PerformanceDataset | None = None
    replayed: bool = False


class JsonAnalyticsRefreshStore:
    """Atomically persist refresh attempts and fence unfinished work."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    def load(self) -> tuple[AnalyticsRefreshAttempt, ...]:
        with self._locked():
            return self._load_unlocked()

    def begin(
        self,
        *,
        schedule_id: str,
        window_started_at: datetime,
        now: datetime,
    ) -> tuple[AnalyticsRefreshAttempt, bool]:
        schedule_id = self._required(schedule_id, "schedule_id")
        window_started_at = self._timestamp(window_started_at, "window_started_at")
        now = self._timestamp(now, "now")
        attempt_id = self._identity(schedule_id, window_started_at)

        with self._locked():
            attempts = self._load_unlocked()
            existing = next(
                (item for item in attempts if item.attempt_id == attempt_id),
                None,
            )
            if existing is not None:
                if existing.status == "started":
                    existing = replace(existing, status="uncertain")
                    attempts = tuple(
                        existing if item.attempt_id == attempt_id else item
                        for item in attempts
                    )
                    self._write_unlocked(attempts)
                return existing, False

            attempt = AnalyticsRefreshAttempt(
                attempt_id=attempt_id,
                schedule_id=schedule_id,
                window_started_at=window_started_at,
                status="started",
                started_at=now,
            )
            self._write_unlocked((*attempts, attempt))
            return attempt, True

    def complete(
        self,
        attempt: AnalyticsRefreshAttempt,
        dataset: PerformanceDataset,
        *,
        now: datetime,
    ) -> AnalyticsRefreshAttempt:
        return self._finish(
            attempt,
            status="completed",
            now=now,
            record_count=len(dataset.records),
        )

    def fail(
        self,
        attempt: AnalyticsRefreshAttempt,
        *,
        reason: str,
        now: datetime,
    ) -> AnalyticsRefreshAttempt:
        return self._finish(
            attempt,
            status="failed",
            now=now,
            failure_reason=self._required(reason, "failure_reason"),
        )

    def mark_uncertain(
        self,
        attempt: AnalyticsRefreshAttempt,
    ) -> AnalyticsRefreshAttempt:
        with self._locked():
            attempts = self._load_unlocked()
            current = self._active(attempts, attempt)
            updated = replace(current, status="uncertain")
            self._write_unlocked(
                tuple(
                    updated if item.attempt_id == current.attempt_id else item
                    for item in attempts
                )
            )
            return updated

    def _finish(
        self,
        attempt: AnalyticsRefreshAttempt,
        *,
        status: str,
        now: datetime,
        record_count: int | None = None,
        failure_reason: str | None = None,
    ) -> AnalyticsRefreshAttempt:
        now = self._timestamp(now, "now")
        with self._locked():
            attempts = self._load_unlocked()
            current = self._active(attempts, attempt)
            updated = replace(
                current,
                status=status,
                completed_at=now,
                record_count=record_count,
                failure_reason=failure_reason,
            )
            self._write_unlocked(
                tuple(
                    updated if item.attempt_id == current.attempt_id else item
                    for item in attempts
                )
            )
            return updated

    @staticmethod
    def _active(
        attempts: tuple[AnalyticsRefreshAttempt, ...],
        attempt: AnalyticsRefreshAttempt,
    ) -> AnalyticsRefreshAttempt:
        current = next(
            (item for item in attempts if item.attempt_id == attempt.attempt_id),
            None,
        )
        if current != attempt or current.status != "started":
            raise ScheduledAnalyticsRefreshError(
                "refresh attempt is not the active started attempt"
            )
        return current

    def _load_unlocked(self) -> tuple[AnalyticsRefreshAttempt, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != REFRESH_STORE_VERSION:
                raise ScheduledAnalyticsRefreshError(
                    "unsupported analytics refresh snapshot version"
                )
            attempts = tuple(self._attempt(item) for item in payload["attempts"])
            self._validate(attempts)
            return attempts
        except ScheduledAnalyticsRefreshError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ScheduledAnalyticsRefreshError(
                "invalid analytics refresh snapshot"
            ) from error

    def _write_unlocked(
        self,
        attempts: tuple[AnalyticsRefreshAttempt, ...],
    ) -> None:
        self._validate(attempts)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": REFRESH_STORE_VERSION,
            "attempts": [
                {
                    **asdict(item),
                    "window_started_at": item.window_started_at.isoformat(),
                    "started_at": item.started_at.isoformat(),
                    "completed_at": (
                        item.completed_at.isoformat()
                        if item.completed_at is not None
                        else None
                    ),
                }
                for item in attempts
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
    def _attempt(cls, value: dict[str, object]) -> AnalyticsRefreshAttempt:
        if not isinstance(value, dict):
            raise ScheduledAnalyticsRefreshError("refresh attempt must be an object")

        completed_at = value.get("completed_at")
        record_count = value.get("record_count")

        return AnalyticsRefreshAttempt(
            attempt_id=cls._required(value["attempt_id"], "attempt_id"),
            schedule_id=cls._required(value["schedule_id"], "schedule_id"),
            window_started_at=datetime.fromisoformat(
                cls._required(value["window_started_at"], "window_started_at")
            ),
            status=cls._required(value["status"], "status"),
            started_at=datetime.fromisoformat(
                cls._required(value["started_at"], "started_at")
            ),
            completed_at=(
                datetime.fromisoformat(cls._required(completed_at, "completed_at"))
                if completed_at is not None
                else None
            ),
            record_count=(
                cls._count(record_count) if record_count is not None else None
            ),
            failure_reason=cls._optional(value.get("failure_reason")),
        )

    @classmethod
    def _validate(
        cls,
        attempts: tuple[AnalyticsRefreshAttempt, ...],
    ) -> None:
        identities = tuple(item.attempt_id for item in attempts)
        if len(identities) != len(set(identities)):
            raise ScheduledAnalyticsRefreshError(
                "analytics refresh attempt IDs must be unique"
            )

        for item in attempts:
            if item.status not in REFRESH_STATUSES:
                raise ScheduledAnalyticsRefreshError(
                    f"unsupported analytics refresh status: {item.status}"
                )

            cls._timestamp(item.window_started_at, "window_started_at")
            cls._timestamp(item.started_at, "started_at")

            expected = cls._identity(
                item.schedule_id,
                item.window_started_at,
            )
            if item.attempt_id != expected:
                raise ScheduledAnalyticsRefreshError(
                    "refresh attempt identity does not match its window"
                )

            if item.status == "completed":
                if item.completed_at is None or item.record_count is None:
                    raise ScheduledAnalyticsRefreshError(
                        "completed refresh attempt is missing its outcome"
                    )
            elif item.status == "failed":
                if item.completed_at is None or item.failure_reason is None:
                    raise ScheduledAnalyticsRefreshError(
                        "failed refresh attempt is missing its outcome"
                    )
            elif any(
                value is not None
                for value in (
                    item.completed_at,
                    item.record_count,
                    item.failure_reason,
                )
            ):
                raise ScheduledAnalyticsRefreshError(
                    "unfinished refresh attempt contains an outcome"
                )

            if item.completed_at is not None:
                cls._timestamp(item.completed_at, "completed_at")

    @staticmethod
    def _identity(schedule_id: str, window_started_at: datetime) -> str:
        window = window_started_at.astimezone(UTC).isoformat()
        digest = hashlib.sha256(f"{schedule_id}\0{window}".encode()).hexdigest()
        return f"analytics-refresh-{digest[:24]}"

    @staticmethod
    def _timestamp(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ScheduledAnalyticsRefreshError(f"{field} must include a timezone")
        return value.astimezone(UTC)

    @staticmethod
    def _required(value: object, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ScheduledAnalyticsRefreshError(f"{field} must not be empty")
        return value.strip()

    @staticmethod
    def _count(value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ScheduledAnalyticsRefreshError(
                "record_count must be a non-negative integer"
            )
        return value

    @classmethod
    def _optional(cls, value: object) -> str | None:
        return (
            None
            if value is None
            else cls._required(
                value,
                "optional value",
            )
        )


class ScheduledAnalyticsRefreshService:
    """Execute only the latest due window for each analytics schedule."""

    def due_window(
        self,
        schedule: AnalyticsRefreshSchedule,
        *,
        now: datetime,
    ) -> datetime | None:
        schedule = self._schedule(schedule)
        now = self._timestamp(now, "now")

        if now < schedule.starts_at:
            return None

        elapsed = now - schedule.starts_at
        windows = elapsed // schedule.interval
        return schedule.starts_at + (schedule.interval * windows)

    def ready(
        self,
        schedules: Iterable[AnalyticsRefreshSchedule],
        *,
        now: datetime,
    ) -> tuple[tuple[AnalyticsRefreshSchedule, datetime], ...]:
        ready: list[tuple[AnalyticsRefreshSchedule, datetime]] = []

        for schedule in schedules:
            normalized = self._schedule(schedule)
            window = self.due_window(normalized, now=now)
            if window is not None:
                ready.append((normalized, window))

        return tuple(
            sorted(
                ready,
                key=lambda item: (
                    item[1],
                    item[0].schedule_id,
                ),
            )
        )

    def refresh(
        self,
        schedule: AnalyticsRefreshSchedule,
        connector: Any,
        store: JsonAnalyticsRefreshStore,
        *,
        now: datetime,
    ) -> ScheduledAnalyticsRefreshResult:
        schedule = self._schedule(schedule)
        now = self._timestamp(now, "now")
        window = self.due_window(schedule, now=now)

        if window is None:
            return ScheduledAnalyticsRefreshResult(attempt=None)

        attempt, acquired = store.begin(
            schedule_id=schedule.schedule_id,
            window_started_at=window,
            now=now,
        )
        if not acquired:
            return ScheduledAnalyticsRefreshResult(
                attempt=attempt,
                replayed=True,
            )

        try:
            dataset = connector.ingest(schedule.publications)
        except Exception as error:
            failed = store.fail(
                attempt,
                reason=self._failure_reason(error),
                now=now,
            )
            return ScheduledAnalyticsRefreshResult(attempt=failed)
        except BaseException:
            store.mark_uncertain(attempt)
            raise

        completed = store.complete(attempt, dataset, now=now)
        return ScheduledAnalyticsRefreshResult(
            attempt=completed,
            dataset=dataset,
        )

    @classmethod
    def _schedule(
        cls,
        schedule: AnalyticsRefreshSchedule,
    ) -> AnalyticsRefreshSchedule:
        schedule_id = JsonAnalyticsRefreshStore._required(
            schedule.schedule_id,
            "schedule_id",
        )
        starts_at = cls._timestamp(schedule.starts_at, "starts_at")

        if schedule.interval <= timedelta(0):
            raise ScheduledAnalyticsRefreshError("interval must be greater than zero")
        if not schedule.publications:
            raise ScheduledAnalyticsRefreshError(
                "analytics schedule requires at least one publication"
            )

        identities: set[tuple[str, str]] = set()
        publications: list[InstagramPublication] = []

        for publication in schedule.publications:
            asset_id = JsonAnalyticsRefreshStore._required(
                publication.asset_id,
                "asset_id",
            )
            media_id = JsonAnalyticsRefreshStore._required(
                publication.media_id,
                "media_id",
            )
            identity = (asset_id, media_id)
            if identity in identities:
                raise ScheduledAnalyticsRefreshError(
                    "analytics schedule contains duplicate publications"
                )
            identities.add(identity)
            publications.append(
                InstagramPublication(
                    asset_id=asset_id,
                    media_id=media_id,
                )
            )

        return AnalyticsRefreshSchedule(
            schedule_id=schedule_id,
            publications=tuple(publications),
            interval=schedule.interval,
            starts_at=starts_at,
        )

    @staticmethod
    def _timestamp(value: datetime, field: str) -> datetime:
        return JsonAnalyticsRefreshStore._timestamp(value, field)

    @staticmethod
    def _failure_reason(error: Exception) -> str:
        message = str(error).strip()
        return (
            error.__class__.__name__
            if not message
            else (f"{error.__class__.__name__}: {message}")
        )
