"""Deterministic release-date campaign timeline models."""

from dataclasses import dataclass
from datetime import date

VALID_RELEASE_TIMELINE_CATEGORIES = frozenset(
    {
        "Artwork",
        "Follow-up",
        "Live",
        "Playlist",
        "Press",
        "Release",
        "Social",
        "Teaser",
        "Video",
    }
)


@dataclass(frozen=True, order=True, slots=True)
class CampaignReleaseTimelineEvent:
    """One dated milestone in a release rollout."""

    date: date
    day_offset: int
    title: str
    category: str
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.date, date):
            raise ValueError("date must be a date")
        if not isinstance(self.day_offset, int) or isinstance(self.day_offset, bool):
            raise ValueError("day_offset must be an integer")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if self.category not in VALID_RELEASE_TIMELINE_CATEGORIES:
            raise ValueError(f"unsupported timeline category: {self.category}")
        if not self.description.strip():
            raise ValueError("description must not be empty")


@dataclass(frozen=True, slots=True)
class CampaignReleaseTimeline:
    """Complete chronological release rollout."""

    release_date: date
    campaign_type: str
    events: tuple[CampaignReleaseTimelineEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.release_date, date):
            raise ValueError("release_date must be a date")
        if not self.campaign_type.strip():
            raise ValueError("campaign_type must not be empty")
        if tuple(sorted(self.events)) != self.events:
            raise ValueError("timeline events must be ordered chronologically")
        if not any(event.day_offset == 0 for event in self.events):
            raise ValueError("timeline must include a release-day event")
