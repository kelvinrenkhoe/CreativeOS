"""Durable storage for bounded campaign orchestration event history."""

import json
from dataclasses import asdict, dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Iterable, Protocol

EVENT_STORE_VERSION = "1"


class OrchestrationEventStoreError(Exception):
    """Base exception for orchestration event persistence."""


class OrchestrationEventStoreCorruptedError(OrchestrationEventStoreError):
    """Raised when persisted orchestration history cannot be decoded."""


class OrchestrationEventStoreVersionError(OrchestrationEventStoreError):
    """Raised when persisted history uses an unsupported schema version."""


class EventLike(Protocol):
    """Minimal event shape accepted from the orchestration API."""

    kind: str
    step: int
    campaign_id: str
    stage: str | None
    action: str | None
    request_id: str | None
    detail: str | None


@dataclass(frozen=True, slots=True)
class StoredOrchestrationEvent:
    """One durable orchestration event associated with a bounded run."""

    run_id: str
    policy: str
    sequence: int
    kind: str
    step: int
    campaign_id: str
    stage: str | None = None
    action: str | None = None
    request_id: str | None = None
    detail: str | None = None


class JsonOrchestrationEventStore:
    """Persist deterministic, versioned event history as one file per campaign."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def append(
        self,
        *,
        campaign_id: str,
        run_id: str,
        policy: str,
        events: Iterable[EventLike],
    ) -> tuple[StoredOrchestrationEvent, ...]:
        """Atomically append one orchestration run's ordered events."""
        campaign_id = self._safe(campaign_id, "campaign_id")
        run_id = self._required(run_id, "run_id")
        policy = self._required(policy, "policy")
        source_events = tuple(events)
        if any(event.campaign_id != campaign_id for event in source_events):
            raise ValueError("event campaign IDs must match campaign_id")

        existing = self.load(campaign_id)
        if any(item.run_id == run_id for item in existing):
            raise ValueError(f"orchestration run already exists: {run_id}")

        stored = tuple(
            StoredOrchestrationEvent(
                run_id=run_id,
                policy=policy,
                sequence=sequence,
                kind=self._required(event.kind, "event.kind"),
                step=self._step(event.step),
                campaign_id=campaign_id,
                stage=event.stage,
                action=event.action,
                request_id=event.request_id,
                detail=event.detail,
            )
            for sequence, event in enumerate(source_events, start=1)
        )
        self._save(campaign_id, existing + stored)
        return stored

    def load(self, campaign_id: str) -> tuple[StoredOrchestrationEvent, ...]:
        """Load complete event history in persisted order."""
        campaign_id = self._safe(campaign_id, "campaign_id")
        path = self.directory / f"{campaign_id}.json"
        if not path.exists():
            return ()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (JSONDecodeError, UnicodeDecodeError) as exc:
            raise OrchestrationEventStoreCorruptedError(
                f"orchestration event history is corrupt: {campaign_id}"
            ) from exc
        if not isinstance(payload, dict) or payload.get("version") != EVENT_STORE_VERSION:
            version = payload.get("version") if isinstance(payload, dict) else None
            raise OrchestrationEventStoreVersionError(
                f"unsupported orchestration event history version: {version}"
            )
        raw_events = payload.get("events")
        if not isinstance(raw_events, list):
            raise OrchestrationEventStoreCorruptedError("events must be a list")
        try:
            events = tuple(StoredOrchestrationEvent(**item) for item in raw_events)
        except (TypeError, ValueError) as exc:
            raise OrchestrationEventStoreCorruptedError("events have an invalid structure") from exc
        if any(item.campaign_id != campaign_id for item in events):
            raise OrchestrationEventStoreCorruptedError("event campaign IDs do not match file name")
        return events

    def _save(self, campaign_id: str, events: tuple[StoredOrchestrationEvent, ...]) -> None:
        path = self.directory / f"{campaign_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"version": EVENT_STORE_VERSION, "events": [asdict(item) for item in events]},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized

    @classmethod
    def _safe(cls, value: str, field: str) -> str:
        normalized = cls._required(value, field)
        if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError(f"{field} must be a safe file name")
        return normalized

    @staticmethod
    def _step(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("event.step must be a non-negative integer")
        return value
