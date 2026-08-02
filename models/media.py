"""Reusable immutable models for campaign media intelligence."""

from dataclasses import dataclass
from enum import StrEnum


class MediaError(ValueError):
    """Reject invalid media intelligence input."""


class MediaChannel(StrEnum):
    PRESS = "press"
    BLOG = "blog"
    PLAYLIST = "playlist"
    INTERVIEW = "interview"
    EPK = "epk"
    SOCIAL = "social"


class MediaGoal(StrEnum):
    AWARENESS = "awareness"
    DISCOVERY = "discovery"
    COVERAGE = "coverage"
    INTERVIEW = "interview"
    STREAMS = "streams"


@dataclass(frozen=True, slots=True)
class MediaContext:
    """Shared campaign context used by media generators."""

    campaign_id: str
    campaign_name: str
    campaign_week: int
    artist: str
    audience: str
    tone: str
    objective: str
    call_to_action: str

    def __post_init__(self) -> None:
        if self.campaign_week < 1:
            raise MediaError("campaign_week must be at least 1")
        for field_name in (
            "campaign_id",
            "campaign_name",
            "artist",
            "audience",
            "tone",
            "objective",
            "call_to_action",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise MediaError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
