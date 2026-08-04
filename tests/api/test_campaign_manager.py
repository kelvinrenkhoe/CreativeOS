"""Tests for deterministic campaign manager decisions."""

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from api.campaign_manager import CampaignManagerAPI
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


def task(asset: str, scheduled: date, priority: int = 10) -> CampaignTask:
    return CampaignTask(
        request_id=f"request-{asset}",
        asset_id=asset,
        media_type="video",
        provider="local",
        scheduled_for=datetime.combine(scheduled, datetime.min.time(), tzinfo=UTC),
        status="scheduled",
        priority=priority,
    )


class DashboardStub:
    def __init__(self, **changes) -> None:
        values = {
            "current_phase": "Promotion",
            "next_milestone": "Release day",
            "warnings": (),
            "errors": (),
        }
        values.update(changes)
        self.result = SimpleNamespace(**values)
        self.reference_date = None

    def summary(self, _campaign, *, today):
        self.reference_date = today
        return self.result


class TasksStub:
    def __init__(self, **changes) -> None:
        values = {"overdue": (), "due_today": (), "warnings": (), "errors": ()}
        values.update(changes)
        self.result = SimpleNamespace(**values)
        self.reference_date = None

    def today(self, _campaign, *, today):
        self.reference_date = today
        return self.result


def manager(tmp_path: Path, dashboard=None, tasks=None) -> CampaignManagerAPI:
    return CampaignManagerAPI(
        project(tmp_path),
        dashboard_api=dashboard or DashboardStub(),
        tasks_api=tasks or TasksStub(),
    )


def test_overdue_task_is_highest_priority(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    overdue = task("teaser-video", date(2026, 8, 3))
    result = manager(tmp_path, tasks=TasksStub(overdue=(overdue,))).today(
        "No Lose Guard", today=reference
    )

    assert result.successful
    assert result.task == overdue
    assert result.priority_action == "Complete overdue task: teaser-video"
    assert "2026-08-03" in result.reason


def test_due_today_follows_overdue_priority(tmp_path: Path) -> None:
    reference = date(2026, 8, 4)
    current = task("cover-post", reference)
    result = manager(tmp_path, tasks=TasksStub(due_today=(current,))).today(
        "No Lose Guard", today=reference
    )

    assert result.task == current
    assert result.priority_action == "Complete today's task: cover-post"


def test_next_milestone_used_when_no_current_tasks(tmp_path: Path) -> None:
    result = manager(tmp_path).today("No Lose Guard", today=date(2026, 8, 4))

    assert result.task is None
    assert result.priority_action == "Prepare for milestone: Release day"


def test_readiness_review_used_when_no_milestone(tmp_path: Path) -> None:
    result = manager(
        tmp_path,
        dashboard=DashboardStub(next_milestone=None),
    ).today("No Lose Guard", today=date(2026, 8, 4))

    assert result.priority_action == "Review campaign readiness"


def test_errors_block_action_and_preserve_context(tmp_path: Path) -> None:
    result = manager(
        tmp_path,
        dashboard=DashboardStub(errors=("Campaign missing",)),
        tasks=TasksStub(errors=("Queue invalid",)),
    ).today("No Lose Guard", today=date(2026, 8, 4))

    assert not result.successful
    assert result.priority_action is None
    assert result.errors == ("Campaign missing", "Queue invalid")
    assert result.current_phase == "Promotion"


def test_warnings_are_deduplicated(tmp_path: Path) -> None:
    result = manager(
        tmp_path,
        dashboard=DashboardStub(warnings=("Shared",)),
        tasks=TasksStub(warnings=("Shared", "Queue warning")),
    ).today("No Lose Guard", today=date(2026, 8, 4))

    assert result.warnings == ("Shared", "Queue warning")


def test_reference_date_is_passed_to_dependencies(tmp_path: Path) -> None:
    dashboard = DashboardStub()
    tasks = TasksStub()
    reference = date(2026, 8, 4)

    manager(tmp_path, dashboard=dashboard, tasks=tasks).today(
        "No Lose Guard", today=reference
    )

    assert dashboard.reference_date == reference
    assert tasks.reference_date == reference
