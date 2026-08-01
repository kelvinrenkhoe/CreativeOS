"""Tests for validated multi-week campaign timeline models."""

from datetime import date, timedelta

import pytest

from models.campaign_timeline import (
    TIMELINE_VERSION,
    CampaignPhase,
    CampaignTimeline,
    CampaignTimelineError,
    CampaignWeek,
)
from services.weekly_content_plan import WeeklyContentItem


def item(day: date, index: int) -> WeeklyContentItem:
    return WeeklyContentItem(
        item_id=f"content-{index}",
        scheduled_date=day,
        platform="instagram",
        format="video-story",
        concept=f"concept-{index}",
        angle=f"angle-{index}",
        call_to_action="Stream now",
    )


def week(
    week_number: int,
    start: date,
    phase: CampaignPhase = CampaignPhase.INTRODUCTION,
) -> CampaignWeek:
    return CampaignWeek(
        week_number=week_number,
        phase=phase,
        objective=f"Objective {week_number}",
        start_date=start,
        items=tuple(item(start + timedelta(days=index), index) for index in range(7)),
    )


def test_campaign_week_exposes_end_date_and_normalizes_objective() -> None:
    start = date(2026, 8, 3)
    campaign_week = CampaignWeek(
        week_number=1,
        phase=CampaignPhase.INTRODUCTION,
        objective="  Introduce the release  ",
        start_date=start,
        items=tuple(item(start + timedelta(days=index), index) for index in range(7)),
    )

    assert campaign_week.objective == "Introduce the release"
    assert campaign_week.end_date == date(2026, 8, 9)


def test_campaign_timeline_accepts_ordered_consecutive_weeks() -> None:
    start = date(2026, 8, 3)
    timeline = CampaignTimeline(
        campaign_id="  no-lose-guard  ",
        start_date=start,
        duration_weeks=2,
        weeks=(
            week(1, start),
            week(2, start + timedelta(weeks=1), CampaignPhase.DISCOVERY),
        ),
    )

    assert timeline.campaign_id == "no-lose-guard"
    assert timeline.version == TIMELINE_VERSION
    assert timeline.end_date == date(2026, 8, 16)
    assert tuple(value.phase for value in timeline.weeks) == (
        CampaignPhase.INTRODUCTION,
        CampaignPhase.DISCOVERY,
    )


@pytest.mark.parametrize("duration", (0, -1, True, 1.5))
def test_campaign_timeline_rejects_invalid_duration(duration) -> None:
    with pytest.raises(CampaignTimelineError, match="duration_weeks"):
        CampaignTimeline(
            campaign_id="campaign-1",
            start_date=date(2026, 8, 3),
            duration_weeks=duration,
            weeks=(),
        )


def test_campaign_timeline_rejects_out_of_order_weeks() -> None:
    start = date(2026, 8, 3)

    with pytest.raises(CampaignTimelineError, match="ordered and consecutively numbered"):
        CampaignTimeline(
            campaign_id="campaign-1",
            start_date=start,
            duration_weeks=2,
            weeks=(
                week(2, start),
                week(1, start + timedelta(weeks=1)),
            ),
        )


def test_campaign_timeline_rejects_non_consecutive_week_dates() -> None:
    start = date(2026, 8, 3)

    with pytest.raises(CampaignTimelineError, match="consecutive seven-day intervals"):
        CampaignTimeline(
            campaign_id="campaign-1",
            start_date=start,
            duration_weeks=2,
            weeks=(
                week(1, start),
                week(2, start + timedelta(weeks=2)),
            ),
        )


def test_campaign_week_rejects_non_planned_items() -> None:
    start = date(2026, 8, 3)
    items = list(item(start + timedelta(days=index), index) for index in range(7))
    items[-1] = WeeklyContentItem(
        item_id="content-published",
        scheduled_date=start + timedelta(days=6),
        platform="instagram",
        format="video-story",
        concept="final-concept",
        angle="final-angle",
        call_to_action="Stream now",
        status="published",
    )

    with pytest.raises(CampaignTimelineError, match="must remain planned"):
        CampaignWeek(
            week_number=1,
            phase=CampaignPhase.INTRODUCTION,
            objective="Introduce the release",
            start_date=start,
            items=tuple(items),
        )


def test_campaign_timeline_rejects_unsupported_version() -> None:
    start = date(2026, 8, 3)

    with pytest.raises(CampaignTimelineError, match="unsupported"):
        CampaignTimeline(
            campaign_id="campaign-1",
            start_date=start,
            duration_weeks=1,
            weeks=(week(1, start),),
            version=TIMELINE_VERSION + 1,
        )
