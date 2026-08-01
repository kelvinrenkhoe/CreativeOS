"""Tests for deterministic campaign recovery proposals."""

from datetime import date, timedelta

import pytest

from models.campaign_dependency_graph import CampaignDependency, CampaignDependencyGraph
from models.campaign_recovery import CampaignRecoveryError, RecoveryRequest
from models.campaign_timeline import CampaignPhase, CampaignTimeline, CampaignWeek
from services.campaign_execution import CampaignExecutionService
from services.campaign_recovery import CampaignRecoveryService
from services.weekly_content_plan import WeeklyContentItem

ITEM_IDS = (
    "announcement",
    "quote",
    "behind-scenes",
    "lyric-video",
    "release-day",
    "fan-reaction",
    "playlist-push",
)


def item(item_id: str, index: int) -> WeeklyContentItem:
    return WeeklyContentItem(
        item_id=item_id,
        scheduled_date=date(2026, 9, 1) + timedelta(days=index),
        platform="instagram",
        format="video-short",
        concept=item_id,
        angle=f"angle-{index}",
        call_to_action="Listen now",
    )


def timeline() -> CampaignTimeline:
    week = CampaignWeek(
        week_number=1,
        phase=CampaignPhase.CONVERSION,
        objective="Launch No Lose Guard",
        start_date=date(2026, 9, 1),
        items=tuple(item(item_id, index) for index, item_id in enumerate(ITEM_IDS)),
    )
    return CampaignTimeline(
        campaign_id="no-lose-guard",
        start_date=date(2026, 9, 1),
        duration_weeks=1,
        weeks=(week,),
    )


def graph() -> CampaignDependencyGraph:
    return CampaignDependencyGraph(
        item_ids=ITEM_IDS,
        dependencies=(
            CampaignDependency("announcement", "behind-scenes"),
            CampaignDependency("announcement", "lyric-video"),
            CampaignDependency("lyric-video", "release-day"),
            CampaignDependency("release-day", "fan-reaction"),
            CampaignDependency("release-day", "playlist-push"),
        ),
    )


def execution(completed=()):
    return CampaignExecutionService().evaluate(timeline(), graph(), completed)


def test_no_op_recovery_preserves_original_order() -> None:
    plan = CampaignRecoveryService().recover(
        timeline(),
        graph(),
        execution(),
        RecoveryRequest(()),
    )

    assert plan.recovered_item_ids == ITEM_IDS
    assert plan.actions == ()
    assert not plan.changed


def test_missed_item_moves_to_next_safe_position() -> None:
    plan = CampaignRecoveryService().recover(
        timeline(),
        graph(),
        execution(("announcement",)),
        RecoveryRequest(("quote",)),
    )

    assert plan.recovered_item_ids == (
        "announcement",
        "behind-scenes",
        "lyric-video",
        "quote",
        "release-day",
        "fan-reaction",
        "playlist-push",
    )
    assert plan.actions[0].item_id == "quote"
    assert plan.actions[0].original_position == 2
    assert plan.actions[0].recovered_position == 4
    assert plan.changed


def test_fixed_milestone_keeps_original_position() -> None:
    plan = CampaignRecoveryService().recover(
        timeline(),
        graph(),
        execution(("announcement",)),
        RecoveryRequest(("quote",), fixed_milestone_ids=("release-day",)),
    )

    assert plan.recovered_item_ids.index("release-day") == ITEM_IDS.index("release-day")
    assert plan.fixed_milestone_ids == ("release-day",)


def test_recovery_preserves_dependency_order() -> None:
    plan = CampaignRecoveryService().recover(
        timeline(),
        graph(),
        execution(("announcement",)),
        RecoveryRequest(("lyric-video",)),
    )

    positions = {item_id: index for index, item_id in enumerate(plan.recovered_item_ids)}
    for dependency in graph().dependencies:
        assert positions[dependency.prerequisite_id] < positions[dependency.dependent_id]


def test_recovery_rejects_unknown_or_completed_missed_items() -> None:
    service = CampaignRecoveryService()

    with pytest.raises(CampaignRecoveryError, match="unknown campaign content item"):
        service.recover(timeline(), graph(), execution(), RecoveryRequest(("missing",)))

    with pytest.raises(CampaignRecoveryError, match="completed content cannot be missed"):
        service.recover(
            timeline(),
            graph(),
            execution(("announcement",)),
            RecoveryRequest(("announcement",)),
        )


def test_recovery_rejects_missed_fixed_overlap() -> None:
    with pytest.raises(CampaignRecoveryError, match="cannot also be fixed"):
        RecoveryRequest(("release-day",), fixed_milestone_ids=("release-day",))


def test_impossible_fixed_milestone_fails_closed() -> None:
    with pytest.raises(CampaignRecoveryError, match="fixed milestone cannot remain"):
        CampaignRecoveryService().recover(
            timeline(),
            graph(),
            execution(("announcement",)),
            RecoveryRequest(("lyric-video",), fixed_milestone_ids=("release-day",)),
        )
