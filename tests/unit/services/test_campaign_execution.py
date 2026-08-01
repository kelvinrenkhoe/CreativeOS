"""Tests for deterministic campaign execution decisions."""

from datetime import date, timedelta

import pytest

from models import (
    CampaignDependency,
    CampaignDependencyGraph,
    CampaignPhase,
    CampaignTimeline,
    CampaignWeek,
)
from services.campaign_execution import CampaignExecutionError, CampaignExecutionService
from services.weekly_content_plan import WeeklyContentItem


def item(item_id: str, scheduled_date: date) -> WeeklyContentItem:
    return WeeklyContentItem(
        item_id=item_id,
        scheduled_date=scheduled_date,
        platform="instagram",
        format="video-short",
        concept=item_id,
        angle="story",
        call_to_action="Listen now",
    )


def timeline(item_ids: tuple[str, ...] | None = None) -> CampaignTimeline:
    item_ids = item_ids or tuple(f"item-{index}" for index in range(1, 8))
    start = date(2026, 8, 3)
    return CampaignTimeline(
        campaign_id="no-lose-guard",
        start_date=start,
        duration_weeks=1,
        weeks=(
            CampaignWeek(
                week_number=1,
                phase=CampaignPhase.INTRODUCTION,
                objective="Introduce the campaign story",
                start_date=start,
                items=tuple(
                    item(item_id, start + timedelta(days=index))
                    for index, item_id in enumerate(item_ids)
                ),
            ),
        ),
    )


def graph(item_ids: tuple[str, ...] | None = None) -> CampaignDependencyGraph:
    item_ids = item_ids or tuple(f"item-{index}" for index in range(1, 8))
    return CampaignDependencyGraph(
        item_ids=item_ids,
        dependencies=tuple(
            CampaignDependency(item_ids[index], item_ids[index + 1])
            for index in range(len(item_ids) - 1)
        ),
    )


def test_execution_selects_first_ready_timeline_item() -> None:
    state = CampaignExecutionService().evaluate(timeline(), graph())

    assert state.next_item_id == "item-1"
    assert state.ready_item_ids == ("item-1",)
    assert tuple(blocked.item_id for blocked in state.blocked_items) == tuple(
        f"item-{index}" for index in range(2, 8)
    )
    assert state.next_reason == "Earliest timeline item with all prerequisites completed."


def test_execution_advances_only_from_explicit_completion() -> None:
    state = CampaignExecutionService().evaluate(
        timeline(),
        graph(),
        completed_item_ids=("item-1", "item-2"),
    )

    assert state.completed_item_ids == ("item-1", "item-2")
    assert state.next_item_id == "item-3"
    assert state.ready_item_ids == ("item-3",)
    assert state.remaining_item_ids == tuple(f"item-{index}" for index in range(3, 8))


def test_execution_preserves_timeline_priority_for_multiple_ready_items() -> None:
    item_ids = ("later-id", "earlier-id", "third", "fourth", "fifth", "sixth", "seventh")
    dependency_graph = CampaignDependencyGraph(item_ids=item_ids)

    state = CampaignExecutionService().evaluate(timeline(item_ids), dependency_graph)

    assert state.ready_item_ids == item_ids
    assert state.next_item_id == "later-id"


def test_execution_reports_completed_campaign() -> None:
    item_ids = tuple(f"item-{index}" for index in range(1, 8))
    state = CampaignExecutionService().evaluate(
        timeline(item_ids),
        graph(item_ids),
        completed_item_ids=item_ids,
    )

    assert state.is_complete is True
    assert state.remaining_item_ids == ()
    assert state.ready_item_ids == ()
    assert state.blocked_items == ()
    assert state.next_item_id is None
    assert state.next_reason is None


def test_execution_rejects_timeline_items_missing_from_graph() -> None:
    with pytest.raises(CampaignExecutionError, match="missing from dependency graph"):
        CampaignExecutionService().evaluate(
            timeline(),
            CampaignDependencyGraph(item_ids=tuple(f"item-{index}" for index in range(1, 7))),
        )


def test_execution_rejects_graph_items_missing_from_timeline() -> None:
    graph_ids = (*tuple(f"item-{index}" for index in range(1, 8)), "extra")
    with pytest.raises(CampaignExecutionError, match="missing from timeline"):
        CampaignExecutionService().evaluate(timeline(), CampaignDependencyGraph(graph_ids))


def test_execution_rejects_duplicate_timeline_item_ids() -> None:
    duplicate_ids = ("duplicate", "duplicate", "three", "four", "five", "six", "seven")
    dependency_graph = CampaignDependencyGraph(
        item_ids=("duplicate", "three", "four", "five", "six", "seven")
    )

    with pytest.raises(CampaignExecutionError, match="timeline content item IDs must be unique"):
        CampaignExecutionService().evaluate(timeline(duplicate_ids), dependency_graph)
