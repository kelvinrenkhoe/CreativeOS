"""Tests for release-date campaign timeline models."""

from datetime import date

import pytest

from models.campaign_release_timeline import (
    CampaignReleaseTimeline,
    CampaignReleaseTimelineEvent,
)


def event(*, day_offset: int = 0) -> CampaignReleaseTimelineEvent:
    return CampaignReleaseTimelineEvent(
        date=date(2026, 9, 1),
        day_offset=day_offset,
        title="Release day",
        category="Release",
        description="Publish the release announcement.",
    )


def test_event_rejects_unsupported_category() -> None:
    with pytest.raises(ValueError, match="unsupported timeline category"):
        CampaignReleaseTimelineEvent(
            date=date(2026, 9, 1),
            day_offset=0,
            title="Release day",
            category="Unknown",
            description="Publish the release announcement.",
        )


def test_timeline_requires_release_day() -> None:
    pre_release = CampaignReleaseTimelineEvent(
        date=date(2026, 8, 31),
        day_offset=-1,
        title="Reminder",
        category="Social",
        description="Publish the final reminder.",
    )

    with pytest.raises(ValueError, match="release-day"):
        CampaignReleaseTimeline(
            release_date=date(2026, 9, 1),
            campaign_type="music-release",
            events=(pre_release,),
        )


def test_timeline_requires_chronological_events() -> None:
    release = event()
    pre_release = CampaignReleaseTimelineEvent(
        date=date(2026, 8, 31),
        day_offset=-1,
        title="Reminder",
        category="Social",
        description="Publish the final reminder.",
    )

    with pytest.raises(ValueError, match="ordered chronologically"):
        CampaignReleaseTimeline(
            release_date=date(2026, 9, 1),
            campaign_type="music-release",
            events=(release, pre_release),
        )
