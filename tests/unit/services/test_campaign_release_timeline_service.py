"""Tests for deterministic campaign release timelines."""

from datetime import date

import pytest

from services.campaign_release_timeline import CampaignReleaseTimelineService


def test_generate_returns_ordered_deterministic_timeline() -> None:
    service = CampaignReleaseTimelineService()

    first = service.generate(date(2026, 9, 1))
    second = service.generate(date(2026, 9, 1))

    assert first == second
    assert tuple(event.date for event in first.events) == tuple(
        sorted(event.date for event in first.events)
    )
    assert first.events[0].day_offset == -21
    assert first.events[-1].day_offset == 7


def test_generate_includes_release_and_follow_up_events() -> None:
    timeline = CampaignReleaseTimelineService().generate(date(2026, 9, 1))

    release = next(event for event in timeline.events if event.day_offset == 0)

    assert release.date == date(2026, 9, 1)
    assert release.category == "Release"
    assert any(event.day_offset > 0 for event in timeline.events)
    assert any(event.category == "Follow-up" for event in timeline.events)
    assert any(event.category == "Playlist" for event in timeline.events)


def test_generate_calculates_expected_dates_from_offsets() -> None:
    timeline = CampaignReleaseTimelineService().generate(date(2026, 9, 1))

    events = {event.day_offset: event for event in timeline.events}

    assert events[-21].date == date(2026, 8, 11)
    assert events[-7].date == date(2026, 8, 25)
    assert events[7].date == date(2026, 9, 8)


def test_generate_rejects_invalid_release_date() -> None:
    with pytest.raises(ValueError, match="release_date must be a date"):
        CampaignReleaseTimelineService().generate("2026-09-01")  # type: ignore[arg-type]


def test_generate_rejects_unsupported_campaign_type() -> None:
    with pytest.raises(ValueError, match="unsupported campaign_type"):
        CampaignReleaseTimelineService().generate(
            date(2026, 9, 1),
            campaign_type="book-launch",
        )
