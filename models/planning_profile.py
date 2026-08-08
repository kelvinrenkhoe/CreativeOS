"""Generic planning profiles for domain-specific campaign timing."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


class PlanningProfileError(ValueError):
    """Raised when domain planning metadata is invalid."""


@dataclass(frozen=True, slots=True)
class MilestoneOffset:
    """A named campaign milestone relative to the profile anchor date."""

    name: str
    offset_days: int

    def __post_init__(self) -> None:
        name = self.name.strip().casefold()
        if not _IDENTIFIER.fullmatch(name):
            raise PlanningProfileError("milestone name must be a safe identifier")
        if isinstance(self.offset_days, bool) or not isinstance(self.offset_days, int):
            raise PlanningProfileError("milestone offset_days must be an integer")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class PlanningProfile:
    """Domain-owned timing semantics resolved around one campaign anchor."""

    anchor_name: str
    start_offset_days: int
    end_offset_days: int
    milestones: tuple[MilestoneOffset, ...]

    def __post_init__(self) -> None:
        anchor_name = self.anchor_name.strip().casefold()
        if not _IDENTIFIER.fullmatch(anchor_name):
            raise PlanningProfileError("anchor_name must be a safe identifier")
        for value, field in (
            (self.start_offset_days, "start_offset_days"),
            (self.end_offset_days, "end_offset_days"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise PlanningProfileError(f"{field} must be an integer")
        names = [milestone.name for milestone in self.milestones]
        if len(names) != len(set(names)):
            raise PlanningProfileError("planning milestone names must be unique")
        if self.start_offset_days > self.end_offset_days:
            raise PlanningProfileError("start_offset_days cannot be after end_offset_days")
        object.__setattr__(self, "anchor_name", anchor_name)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanningProfile":
        """Build a planning profile from domain-pack configuration."""
        if not isinstance(data, dict):
            raise PlanningProfileError("planning profile must be a mapping")
        anchor_name = data.get("anchor")
        start_offset = data.get("start_offset_days")
        end_offset = data.get("end_offset_days")
        raw_milestones = data.get("milestones", {})
        if not isinstance(anchor_name, str):
            raise PlanningProfileError("planning.anchor is required")
        if not isinstance(raw_milestones, dict):
            raise PlanningProfileError("planning.milestones must be a mapping")
        milestones = tuple(MilestoneOffset(name, offset) for name, offset in raw_milestones.items())
        return cls(anchor_name, start_offset, end_offset, milestones)

    def resolve(self, anchor_date: date) -> tuple[date, date, tuple[tuple[str, date], ...]]:
        """Resolve campaign dates and milestones around an explicit anchor date."""
        if not isinstance(anchor_date, date):
            raise PlanningProfileError("anchor_date must be a date")
        start_date = anchor_date + timedelta(days=self.start_offset_days)
        end_date = anchor_date + timedelta(days=self.end_offset_days)
        milestones = tuple(
            (milestone.name, anchor_date + timedelta(days=milestone.offset_days))
            for milestone in self.milestones
        )
        return start_date, end_date, milestones
