"""Validated models for a multi-week campaign content timeline."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from services.weekly_content_plan import WeeklyContentItem

TIMELINE_VERSION = 1


class CampaignTimelineError(ValueError):
    """Reject incomplete or inconsistent campaign timeline data."""


class CampaignPhase(StrEnum):
    """Deterministic stages in a release campaign progression."""

    INTRODUCTION = "introduction"
    DISCOVERY = "discovery"
    ENGAGEMENT = "engagement"
    MOMENTUM = "momentum"
    CONVERSION = "conversion"
    SUSTAIN = "sustain"


@dataclass(frozen=True, slots=True)
class CampaignWeek:
    """One ordered seven-day section of a campaign timeline."""

    week_number: int
    phase: CampaignPhase
    objective: str
    start_date: date
    items: tuple[WeeklyContentItem, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.week_number, int) or isinstance(self.week_number, bool):
            raise CampaignTimelineError("week_number must be an integer")
        if self.week_number < 1:
            raise CampaignTimelineError("week_number must be at least 1")
        if not isinstance(self.phase, CampaignPhase):
            raise CampaignTimelineError("phase must be a CampaignPhase")
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise CampaignTimelineError("objective must be a non-empty string")
        if not isinstance(self.start_date, date):
            raise CampaignTimelineError("start_date must be a date")
        if len(self.items) != 7:
            raise CampaignTimelineError("campaign week must contain exactly seven items")

        expected_dates = tuple(self.start_date + timedelta(days=index) for index in range(7))
        actual_dates = tuple(item.scheduled_date for item in self.items)
        if actual_dates != expected_dates:
            raise CampaignTimelineError(
                "campaign week items must have seven ordered consecutive dates"
            )
        if any(item.status != "planned" for item in self.items):
            raise CampaignTimelineError("campaign week items must remain planned")

        object.__setattr__(self, "objective", self.objective.strip())

    @property
    def end_date(self) -> date:
        """Return the final date covered by this campaign week."""
        return self.start_date + timedelta(days=6)


@dataclass(frozen=True, slots=True)
class CampaignTimeline:
    """An ordered, validated sequence of campaign weeks."""

    campaign_id: str
    start_date: date
    duration_weeks: int
    weeks: tuple[CampaignWeek, ...]
    version: int = TIMELINE_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.campaign_id, str) or not self.campaign_id.strip():
            raise CampaignTimelineError("campaign_id must be a non-empty string")
        if not isinstance(self.start_date, date):
            raise CampaignTimelineError("start_date must be a date")
        if not isinstance(self.duration_weeks, int) or isinstance(self.duration_weeks, bool):
            raise CampaignTimelineError("duration_weeks must be an integer")
        if self.duration_weeks < 1:
            raise CampaignTimelineError("duration_weeks must be at least 1")
        if self.version != TIMELINE_VERSION:
            raise CampaignTimelineError("unsupported campaign timeline version")
        if len(self.weeks) != self.duration_weeks:
            raise CampaignTimelineError("timeline week count must match duration_weeks")

        expected_numbers = tuple(range(1, self.duration_weeks + 1))
        actual_numbers = tuple(week.week_number for week in self.weeks)
        if actual_numbers != expected_numbers:
            raise CampaignTimelineError("timeline weeks must be ordered and consecutively numbered")

        expected_starts = tuple(
            self.start_date + timedelta(weeks=index) for index in range(self.duration_weeks)
        )
        actual_starts = tuple(week.start_date for week in self.weeks)
        if actual_starts != expected_starts:
            raise CampaignTimelineError("timeline weeks must start on consecutive seven-day intervals")

        object.__setattr__(self, "campaign_id", self.campaign_id.strip())

    @property
    def end_date(self) -> date:
        """Return the final date covered by the complete timeline."""
        return self.weeks[-1].end_date
