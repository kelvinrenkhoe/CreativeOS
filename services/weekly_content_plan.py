"""Build and persist deterministic, varied weekly campaign content plans."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

VERSION = 1


class WeeklyContentPlanError(ValueError):
    """Reject impossible plans and invalid persisted state."""


@dataclass(frozen=True, slots=True)
class ContentCandidate:
    platform: str
    format: str
    concept: str
    angle: str
    call_to_action: str


@dataclass(frozen=True, slots=True)
class VarietyConstraints:
    concept_spacing: int = 3
    angle_spacing: int = 2
    video_format_spacing: int = 2


@dataclass(frozen=True, slots=True)
class WeeklyContentItem:
    item_id: str
    scheduled_date: date
    platform: str
    format: str
    concept: str
    angle: str
    call_to_action: str
    status: str = "planned"


@dataclass(frozen=True, slots=True)
class WeeklyContentPlan:
    campaign_id: str
    week_start: date
    items: tuple[WeeklyContentItem, ...]


class WeeklyContentPlanner:
    """Create a deterministic plan that respects recent persisted history."""

    def build(self, campaign_id, week_start, candidates, *, history=(), constraints=None):
        campaign_id = self._required(campaign_id, "campaign_id")
        constraints = constraints or VarietyConstraints()
        if not isinstance(week_start, date):
            raise WeeklyContentPlanError("week_start must be a date")
        for field, value in asdict(constraints).items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise WeeklyContentPlanError(f"{field} must be a non-negative integer")
        candidates = tuple(self._candidate(value) for value in candidates)
        if not candidates:
            raise WeeklyContentPlanError("at least one content candidate is required")
        candidates = tuple(
            sorted(candidates, key=lambda value: self._key(campaign_id, week_start, value))
        )
        recent = tuple(
            item
            for plan in history
            if plan.campaign_id == campaign_id and plan.week_start < week_start
            for item in plan.items
            if item.scheduled_date < week_start
        )
        chosen = self._choose(week_start, candidates, recent, constraints, ())
        if chosen is None:
            raise WeeklyContentPlanError(
                "unable to build seven-day plan with the configured variety constraints"
            )
        items = tuple(self._item(campaign_id, day, candidate) for day, candidate in chosen)
        plan = WeeklyContentPlan(campaign_id, week_start, items)
        self.validate(plan)
        return plan

    def validate(self, plan):
        self._required(plan.campaign_id, "campaign_id")
        expected = tuple(plan.week_start + timedelta(days=index) for index in range(7))
        if tuple(item.scheduled_date for item in plan.items) != expected:
            raise WeeklyContentPlanError("weekly plan must contain seven ordered consecutive dates")
        identities = set()
        for item in plan.items:
            candidate = ContentCandidate(
                item.platform,
                item.format,
                item.concept,
                item.angle,
                item.call_to_action,
            )
            if item.status != "planned" or item.item_id != self._identity(
                plan.campaign_id, item.scheduled_date, candidate
            ):
                raise WeeklyContentPlanError("weekly content item is invalid")
            if item.item_id in identities:
                raise WeeklyContentPlanError("weekly content item identity is duplicated")
            identities.add(item.item_id)

    def _choose(self, start, candidates, history, constraints, chosen):
        if len(chosen) == 7:
            return chosen
        day = start + timedelta(days=len(chosen))
        previous = (
            *history,
            *(self._item("selection", date_, value) for date_, value in chosen),
        )
        for candidate in candidates:
            if self._allowed(candidate, day, previous, constraints):
                result = self._choose(
                    start, candidates, history, constraints, (*chosen, (day, candidate))
                )
                if result is not None:
                    return result
        return None

    @staticmethod
    def _allowed(candidate, day, previous, constraints):
        rules = (
            ("concept", constraints.concept_spacing),
            ("angle", constraints.angle_spacing),
            (
                "format",
                constraints.video_format_spacing if candidate.format.startswith("video") else 0,
            ),
        )
        return all(
            spacing == 0
            or not any(
                getattr(item, field) == getattr(candidate, field)
                and 0 < (day - item.scheduled_date).days < spacing
                for item in previous
            )
            for field, spacing in rules
        )

    @classmethod
    def _candidate(cls, value):
        if not isinstance(value, ContentCandidate):
            raise WeeklyContentPlanError("candidates must be ContentCandidate instances")
        return ContentCandidate(
            *(cls._required(item, field) for field, item in asdict(value).items())
        )

    @classmethod
    def _item(cls, campaign_id, day, candidate):
        return WeeklyContentItem(
            cls._identity(campaign_id, day, candidate), day, *asdict(candidate).values()
        )

    @staticmethod
    def _key(campaign_id, week_start, candidate):
        raw = "\0".join((campaign_id, week_start.isoformat(), *asdict(candidate).values()))
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _identity(campaign_id, day, candidate):
        raw = "\0".join((campaign_id, day.isoformat(), *asdict(candidate).values()))
        return f"content-{hashlib.sha256(raw.encode()).hexdigest()[:24]}"

    @staticmethod
    def _required(value, field):
        if not isinstance(value, str) or not value.strip():
            raise WeeklyContentPlanError(f"{field} must be a non-empty string")
        return value.strip()


class JsonWeeklyContentPlanStore:
    """Atomically persist versioned plans for exactly one campaign."""

    def __init__(self, path: Path, campaign_id: str):
        self.path = path
        self.campaign_id = WeeklyContentPlanner._required(campaign_id, "campaign_id")
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    def load(self):
        with self._locked():
            return self._load()

    def save(self, plan, *, replace=False):
        WeeklyContentPlanner().validate(plan)
        if plan.campaign_id != self.campaign_id:
            raise WeeklyContentPlanError("plan does not belong to this campaign store")
        with self._locked():
            plans = self._load()
            existing = next((value for value in plans if value.week_start == plan.week_start), None)
            if existing == plan:
                return existing
            if existing is not None and not replace:
                raise WeeklyContentPlanError("weekly plan already exists; replacement is required")
            plans = tuple(value for value in plans if value.week_start != plan.week_start) + (plan,)
            plans = tuple(sorted(plans, key=lambda value: value.week_start))
            self._write(plans)
            return plan

    def _load(self):
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != VERSION:
                raise WeeklyContentPlanError("unsupported weekly content plan version")
            if payload.get("campaign_id") != self.campaign_id:
                raise WeeklyContentPlanError("weekly content plan campaign does not match store")
            plans = tuple(self._decode(value) for value in payload["plans"])
            weeks = tuple(value.week_start for value in plans)
            if weeks != tuple(sorted(set(weeks))):
                raise WeeklyContentPlanError("weekly plans must have unique ordered week starts")
            for plan in plans:
                WeeklyContentPlanner().validate(plan)
            return plans
        except WeeklyContentPlanError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise WeeklyContentPlanError("invalid weekly content plan snapshot") from error

    def _write(self, plans):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": VERSION,
            "campaign_id": self.campaign_id,
            "plans": [
                {
                    "campaign_id": plan.campaign_id,
                    "week_start": plan.week_start.isoformat(),
                    "items": [
                        {
                            **asdict(item),
                            "scheduled_date": item.scheduled_date.isoformat(),
                        }
                        for item in plan.items
                    ],
                }
                for plan in plans
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
    def _decode(value):
        return WeeklyContentPlan(
            value["campaign_id"],
            date.fromisoformat(value["week_start"]),
            tuple(
                WeeklyContentItem(
                    **{
                        **item,
                        "scheduled_date": date.fromisoformat(item["scheduled_date"]),
                    }
                )
                for item in value["items"]
            ),
        )
