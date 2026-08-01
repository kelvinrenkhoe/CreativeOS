"""Immutable models for deterministic campaign recovery proposals."""

from dataclasses import dataclass
from enum import StrEnum


class CampaignRecoveryError(ValueError):
    """Reject invalid or impossible campaign recovery requests."""


class RecoveryReason(StrEnum):
    """Supported reasons for deterministic campaign recovery."""

    MISSED_CONTENT = "missed_content"


@dataclass(frozen=True, slots=True)
class RecoveryRequest:
    """Explicit campaign disruption details supplied by the caller."""

    missed_item_ids: tuple[str, ...]
    fixed_milestone_ids: tuple[str, ...] = ()
    reason: RecoveryReason = RecoveryReason.MISSED_CONTENT

    def __post_init__(self) -> None:
        missed = self._normalized(self.missed_item_ids, "missed_item_id")
        fixed = self._normalized(self.fixed_milestone_ids, "fixed_milestone_id")
        if len(missed) != len(set(missed)):
            raise CampaignRecoveryError("missed content item IDs must be unique")
        if len(fixed) != len(set(fixed)):
            raise CampaignRecoveryError("fixed milestone item IDs must be unique")
        if set(missed).intersection(fixed):
            raise CampaignRecoveryError("missed items cannot also be fixed milestones")
        if not isinstance(self.reason, RecoveryReason):
            raise CampaignRecoveryError("reason must be a RecoveryReason")
        object.__setattr__(self, "missed_item_ids", missed)
        object.__setattr__(self, "fixed_milestone_ids", fixed)

    @staticmethod
    def _normalized(values: tuple[str, ...], field: str) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise CampaignRecoveryError(f"{field} must be a non-empty string")
            normalized.append(value.strip())
        return tuple(normalized)


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    """One explainable positional change in the recovered campaign order."""

    item_id: str
    original_position: int
    recovered_position: int
    reason: RecoveryReason


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """A read-only proposed campaign order and its recovery explanation."""

    campaign_id: str
    original_item_ids: tuple[str, ...]
    recovered_item_ids: tuple[str, ...]
    completed_item_ids: tuple[str, ...]
    fixed_milestone_ids: tuple[str, ...]
    actions: tuple[RecoveryAction, ...]

    @property
    def changed(self) -> bool:
        """Return whether recovery changed the campaign item order."""
        return self.original_item_ids != self.recovered_item_ids
