"""Tests for deterministic, durable weekly content planning."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest

from services.weekly_content_plan import (
    ContentCandidate,
    JsonWeeklyContentPlanStore,
    VarietyConstraints,
    WeeklyContentPlanError,
    WeeklyContentPlanner,
)


def candidates():
    return tuple(
        ContentCandidate(
            ("instagram", "tiktok", "facebook")[index % 3],
            ("video-performance", "video-story", "photo", "lyric-card")[index % 4],
            f"concept-{index}",
            f"angle-{index}",
            f"cta-{index}",
        )
        for index in range(8)
    )


def test_builds_deterministic_seven_day_planned_sequence():
    planner = WeeklyContentPlanner()
    first = planner.build("campaign-1", date(2026, 8, 3), candidates())
    assert first == planner.build("campaign-1", date(2026, 8, 3), candidates())
    assert len(first.items) == 7
    assert {item.status for item in first.items} == {"planned"}
    assert len({item.item_id for item in first.items}) == 7


def test_recent_history_prevents_immediate_repetition():
    planner = WeeklyContentPlanner()
    first = planner.build("campaign-1", date(2026, 8, 3), candidates())
    second = planner.build(
        "campaign-1",
        date(2026, 8, 10),
        candidates(),
        history=(first,),
        constraints=VarietyConstraints(concept_spacing=3, angle_spacing=3),
    )
    assert second.items[0].concept not in {item.concept for item in first.items[-2:]}
    assert second.items[0].angle not in {item.angle for item in first.items[-2:]}


def test_impossible_constraints_are_rejected():
    with pytest.raises(WeeklyContentPlanError, match="unable to build"):
        WeeklyContentPlanner().build(
            "campaign-1",
            date(2026, 8, 3),
            candidates()[:1],
            constraints=VarietyConstraints(2),
        )


def test_store_is_idempotent_and_protects_existing_week(tmp_path):
    store = JsonWeeklyContentPlanStore(tmp_path / "plans.json", "campaign-1")
    plan = WeeklyContentPlanner().build("campaign-1", date(2026, 8, 3), candidates())
    assert store.save(plan) == store.save(plan)
    altered = type(plan)(plan.campaign_id, plan.week_start, plan.items[:-1])
    with pytest.raises(WeeklyContentPlanError):
        store.save(altered)


@pytest.mark.parametrize(
    ("payload", "message"),
    (("{", "invalid"), ('{"version":99}', "unsupported")),
)
def test_corrupt_or_unsupported_state_fails_closed(tmp_path, payload, message):
    path = tmp_path / "plans.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(WeeklyContentPlanError, match=message):
        JsonWeeklyContentPlanStore(path, "campaign-1").load()


def test_concurrent_identical_writes_create_one_plan(tmp_path):
    path = tmp_path / "plans.json"
    plan = WeeklyContentPlanner().build("campaign-1", date(2026, 8, 3), candidates())

    def save(_):
        return JsonWeeklyContentPlanStore(path, "campaign-1").save(plan)

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(save, range(8))) == [plan] * 8
    assert JsonWeeklyContentPlanStore(path, "campaign-1").load() == (plan,)
