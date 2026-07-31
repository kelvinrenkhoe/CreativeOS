"""Persist attributable human-review decisions without applying side effects."""

from __future__ import annotations

import fcntl
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.human_review_inbox import (
    HumanReviewInboxService,
    ReviewDecision,
    ReviewInbox,
)

REVIEW_DECISION_STORE_VERSION = 1


class ReviewDecisionStateError(ValueError):
    """Reject invalid, incompatible, or conflicting decision state."""


@dataclass(frozen=True, slots=True)
class StoredReviewDecision:
    """One durable decision tied to its exact review source."""

    review_id: str
    campaign_id: str
    kind: str
    subject_id: str
    decision: str
    decided_by: str
    decided_at: datetime
    reason: str | None = None


class JsonReviewDecisionStore:
    """Atomically persist normalized human-review decisions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    def load(self) -> tuple[StoredReviewDecision, ...]:
        """Load all decisions, or return an empty collection when absent."""
        with self._locked():
            return self._load_unlocked()

    def record(
        self,
        inbox: ReviewInbox,
        decision: ReviewDecision,
        *,
        decided_at: datetime,
    ) -> StoredReviewDecision:
        """Validate and persist one decision idempotently."""
        try:
            outcome = HumanReviewInboxService().review(inbox, (decision,))
        except ValueError as error:
            raise ReviewDecisionStateError(str(error)) from error

        item, normalized = outcome.decided[0]
        if decided_at.tzinfo is None or decided_at.utcoffset() is None:
            raise ReviewDecisionStateError("decided_at must be timezone-aware")

        candidate = StoredReviewDecision(
            review_id=item.review_id,
            campaign_id=item.campaign_id,
            kind=item.kind,
            subject_id=item.subject_id,
            decision=normalized.decision,
            decided_by=normalized.decided_by,
            decided_at=decided_at,
            reason=normalized.reason,
        )

        with self._locked():
            decisions = self._load_unlocked()
            existing = next(
                (stored for stored in decisions if stored.review_id == candidate.review_id),
                None,
            )
            if existing is not None:
                if self._same_decision(existing, candidate):
                    return existing
                raise ReviewDecisionStateError(
                    f"conflicting decision for review_id: {candidate.review_id}"
                )

            updated = (*decisions, candidate)
            self._write_unlocked(updated)
            return candidate

    def _load_unlocked(self) -> tuple[StoredReviewDecision, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("snapshot must be an object")
            if payload.get("version") != REVIEW_DECISION_STORE_VERSION:
                raise ReviewDecisionStateError("unsupported review decision store version")
            decisions = tuple(self._decision(item) for item in payload["decisions"])
            self._validate(decisions)
            return decisions
        except ReviewDecisionStateError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ReviewDecisionStateError("invalid review decision snapshot") from error

    def _write_unlocked(self, decisions: tuple[StoredReviewDecision, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": REVIEW_DECISION_STORE_VERSION,
            "decisions": [
                {
                    **asdict(decision),
                    "decided_at": decision.decided_at.isoformat(),
                }
                for decision in decisions
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
    def _decision(cls, value: object) -> StoredReviewDecision:
        if not isinstance(value, dict):
            raise TypeError("decision must be an object")
        return StoredReviewDecision(
            review_id=cls._required(value["review_id"], "review_id"),
            campaign_id=cls._required(value["campaign_id"], "campaign_id"),
            kind=cls._required(value["kind"], "kind"),
            subject_id=cls._required(value["subject_id"], "subject_id"),
            decision=cls._required(value["decision"], "decision"),
            decided_by=cls._required(value["decided_by"], "decided_by"),
            decided_at=datetime.fromisoformat(cls._required(value["decided_at"], "decided_at")),
            reason=cls._optional(value.get("reason"), "reason"),
        )

    @classmethod
    def _validate(cls, decisions: tuple[StoredReviewDecision, ...]) -> None:
        review_ids: set[str] = set()
        for decision in decisions:
            if decision.review_id in review_ids:
                raise ReviewDecisionStateError(
                    f"duplicate decision for review_id: {decision.review_id}"
                )
            review_ids.add(decision.review_id)
            if decision.decided_at.tzinfo is None or decision.decided_at.utcoffset() is None:
                raise ReviewDecisionStateError("decided_at must be timezone-aware")
            for field in ("campaign_id", "kind", "subject_id", "decision", "decided_by"):
                cls._required(getattr(decision, field), field)

    @staticmethod
    def _same_decision(
        existing: StoredReviewDecision,
        candidate: StoredReviewDecision,
    ) -> bool:
        return (
            existing.review_id,
            existing.campaign_id,
            existing.kind,
            existing.subject_id,
            existing.decision,
            existing.decided_by,
            existing.reason,
        ) == (
            candidate.review_id,
            candidate.campaign_id,
            candidate.kind,
            candidate.subject_id,
            candidate.decision,
            candidate.decided_by,
            candidate.reason,
        )

    @staticmethod
    def _required(value: object, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise TypeError(f"{field} must be a non-empty string")
        return value.strip()

    @classmethod
    def _optional(cls, value: object, field: str) -> str | None:
        return None if value is None else cls._required(value, field)
