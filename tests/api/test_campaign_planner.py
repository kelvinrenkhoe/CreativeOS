"""Tests for the deterministic campaign planner API."""

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from api.campaign_planner import CampaignPlannerAPI
from api.campaign_tasks import CampaignTask
from core.project import Project

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
repository:
  songs: songs
  campaigns: campaigns
  assets: assets
  knowledge: knowledge
"""


def project(root: Path) -> Project:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir()
    return Project(root)


def task(asset: str, scheduled: date, media_type: str = "video", priority: int = 10):
    return CampaignTask(
        request_id=f"request-{asset}",
        asset_id=asset,
        media_type=media_type,
        provider="local",
        scheduled_for=datetime.combine(scheduled, datetime.min.time(), tzinfo=UTC),
        status="scheduled",
        priority=priority,
    )


class TasksStub:
    def __init__(self, **changes) -> None:
        values = {
            "overdue": (),
            "due_today": (),
            "upcoming": (),
            "warnings": (),
            "errors": (),
        }
        values.update(changes)
        self.result = SimpleNamespace(**values)
        self.reference_date = None

    def today(self, _campaign, *, today):
        self.reference_date = today
        return self.result


class TimelineStub:
    def __init__(self, events=(), warnings=(), errors=()) -> None:
        self.result = SimpleNamespace(
            timeline_events=events,
            warnings=warnings,
            errors=errors,
        )

    def timeline(self, _campaign):
        return self.result


class ManagerStub:
    def __init__(self, selected_task=None, warnings=(), errors=()) -> None:
        self.result = SimpleNamespace(
            task=selected_task,
            warnings=warnings,
            errors=errors,
        )
        self.reference_date = None

    def today(self, _campaign, *, today):
        self.reference_date = today
        return self.result


def planner(tmp_path: Path, tasks=None, timeline=None, manager=None):
    return CampaignPlannerAPI(
        project(tmp_path),
        tasks_api=tasks or TasksStub(),
        timeline_api=timeline or TimelineStub(),
        manager_api=manager or ManagerStub(),
    )


def event(day: date, title: str):
    return SimpleNamespace(date=day, title=title)


def test_seven_day_plan_has_inclusive_window(tmp_path: Path) -> None:
    result = planner(tmp_path).plan("No Lose Guard", today=date(2026, 8, 4))

    assert result.start == date(2026, 8, 4)
    assert result.end == date(2026, 8, 10)
    assert len(result.daily_plans) == 7
    assert result.daily_plans[-1].date == date(2026, 8, 10)


def test_one_day_plan(tmp_path: Path) -> None:
    result = planner(tmp_path).plan("No Lose Guard", days=1, today=date(2026, 8, 4))

    assert result.start == result.end
    assert len(result.daily_plans) == 1


def test_invalid_days_returns_structured_error(tmp_path: Path) -> None:
    result = planner(tmp_path).plan("No Lose Guard", days=0, today=date(2026, 8, 4))

    assert not result.successful
    assert result.errors == ("days must be at least 1",)


def test_overdue_tasks_are_placed_on_first_day(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    overdue = task("teaser-video", date(2026, 8, 2))
    result = planner(
        tmp_path,
        tasks=TasksStub(overdue=(overdue,)),
        manager=ManagerStub(selected_task=overdue),
    ).plan("No Lose Guard", today=reference)

    first = result.daily_plans[0]
    assert first.tasks == (overdue,)
    assert first.priority == "high"
    assert first.estimated_minutes == 30


def test_future_tasks_stay_on_scheduled_dates(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    future = task("cover-image", date(2026, 8, 7), media_type="image")
    result = planner(tmp_path, tasks=TasksStub(upcoming=(future,))).plan(
        "No Lose Guard", today=reference
    )

    day = result.daily_plans[3]
    assert day.date == date(2026, 8, 7)
    assert day.tasks == (future,)
    assert day.estimated_minutes == 10


def test_tasks_are_sorted_by_priority_then_identity(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    low = task("low-video", reference, priority=1)
    high_b = task("z-video", reference, priority=20)
    high_a = task("a-video", reference, priority=20)
    result = planner(
        tmp_path,
        tasks=TasksStub(due_today=(low, high_b, high_a)),
    ).plan("No Lose Guard", today=reference)

    assert result.daily_plans[0].tasks == (high_a, high_b, low)


def test_milestone_is_associated_with_matching_day(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    timeline = TimelineStub(events=(event(date(2026, 8, 6), "Spotify pitch"),))
    result = planner(tmp_path, timeline=timeline).plan("No Lose Guard", today=reference)

    assert result.daily_plans[2].milestone == "Spotify pitch"
    assert result.daily_plans[2].priority == "milestone"


def test_effort_estimates_all_supported_task_types(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    tasks = (
        task("caption", reference, "caption"),
        task("artwork", reference, "image"),
        task("master", reference, "audio"),
        task("reel", reference, "video"),
        task("approval-review", reference, "review"),
        task("website", reference, "other"),
    )
    result = planner(tmp_path, tasks=TasksStub(due_today=tasks)).plan(
        "No Lose Guard", today=reference
    )

    assert result.daily_plans[0].estimated_minutes == 105


def test_dependency_errors_block_plan(tmp_path: Path) -> None:
    result = planner(
        tmp_path,
        tasks=TasksStub(errors=("Queue invalid",)),
        timeline=TimelineStub(errors=("Campaign missing",)),
    ).plan("No Lose Guard", today=date(2026, 8, 4))

    assert not result.successful
    assert result.daily_plans == ()
    assert result.errors == ("Queue invalid", "Campaign missing")


def test_warnings_are_aggregated_and_deduplicated(tmp_path: Path) -> None:
    result = planner(
        tmp_path,
        tasks=TasksStub(warnings=("Shared",)),
        timeline=TimelineStub(warnings=("Shared", "Timeline warning")),
        manager=ManagerStub(warnings=("Manager warning",)),
    ).plan("No Lose Guard", today=date(2026, 8, 4))

    assert result.warnings == ("Shared", "Timeline warning", "Manager warning")


def test_reference_date_is_passed_to_dependencies(tmp_path: Path) -> None:
    tasks = TasksStub()
    manager = ManagerStub()
    reference = date(2026, 8, 4)

    planner(tmp_path, tasks=tasks, manager=manager).plan("No Lose Guard", today=reference)

    assert tasks.reference_date == reference
    assert manager.reference_date == reference
