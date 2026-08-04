"""Tests for the campaign execution task API."""

from datetime import UTC, date, datetime
from pathlib import Path

from api.campaign_tasks import CampaignTasksAPI
from core.project import Project
from services.campaign_queue import ExecutionQueue, QueueJob
from services.persistent_queue import JsonExecutionQueueStore, PersistentQueue
from services.provider_execution import ExecutionApproval, ExecutionRequest

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


def create_workspace(root: Path) -> Project:
    """Create the minimum workspace required by task API tests."""
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "campaigns" / "no-lose-guard").mkdir()
    return Project(root)


def job(
    request_id: str,
    scheduled_for: datetime,
    *,
    status: str = "scheduled",
    work_id: str = "no-lose-guard",
    priority: int = 0,
) -> QueueJob:
    """Return one valid queue job for tests."""
    request = ExecutionRequest(
        request_id=request_id,
        asset_id=f"asset-{request_id}",
        work_id=work_id,
        media_type="image",
        provider="test-provider",
        prompt="Create campaign asset",
    )
    approval = ExecutionApproval(
        asset_id=request.asset_id,
        media_type=request.media_type,
        provider=request.provider,
        approved_by="tester",
    )
    return QueueJob(
        request=request,
        approval=approval,
        scheduled_for=scheduled_for,
        priority=priority,
        status=status,
    )


def save(project: Project, *jobs: QueueJob) -> None:
    """Persist queue jobs at the canonical runtime path."""
    path = project.root / ".creativeos" / "runtime" / "execution-queue.json"
    JsonExecutionQueueStore(path).save(
        PersistentQueue(queue=ExecutionQueue(jobs=jobs))
    )


def test_today_classifies_campaign_tasks(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    save(
        project,
        job("overdue", datetime(2026, 8, 3, 10, tzinfo=UTC)),
        job("today", datetime(2026, 8, 4, 10, tzinfo=UTC), priority=5),
        job("upcoming", datetime(2026, 8, 5, 10, tzinfo=UTC)),
        job("completed", datetime(2026, 8, 2, 10, tzinfo=UTC), status="completed"),
    )

    result = CampaignTasksAPI(project).today(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert result.successful
    assert tuple(task.request_id for task in result.overdue) == ("overdue",)
    assert tuple(task.request_id for task in result.due_today) == ("today",)
    assert tuple(task.request_id for task in result.upcoming) == ("upcoming",)
    assert tuple(task.request_id for task in result.completed) == ("completed",)
    assert result.completion_percent == 25


def test_today_ignores_other_campaigns_and_reports_terminal_warnings(
    tmp_path: Path,
) -> None:
    project = create_workspace(tmp_path)
    save(
        project,
        job("failed", datetime(2026, 8, 4, 10, tzinfo=UTC), status="failed"),
        job("cancelled", datetime(2026, 8, 4, 11, tzinfo=UTC), status="cancelled"),
        job(
            "other",
            datetime(2026, 8, 4, 12, tzinfo=UTC),
            work_id="another-campaign",
        ),
    )

    result = CampaignTasksAPI(project).today(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert result.due_today == ()
    assert len(result.warnings) == 2
    assert all("other" not in warning for warning in result.warnings)


def test_today_returns_empty_result_for_campaign_without_jobs(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    result = CampaignTasksAPI(project).today(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert result.successful
    assert result.overdue == ()
    assert result.due_today == ()
    assert result.upcoming == ()
    assert result.completed == ()
    assert result.completion_percent == 0


def test_today_reports_unknown_campaign(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    result = CampaignTasksAPI(project).today(
        "Missing Campaign",
        today=date(2026, 8, 4),
    )

    assert not result.successful
    assert "Campaign workspace not found" in result.errors[0]


def test_today_reports_malformed_queue_dates(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    queue_path = project.root / ".creativeos" / "runtime" / "execution-queue.json"
    queue_path.parent.mkdir(parents=True)
    queue_path.write_text(
        '{"version": 1, "jobs": [{"scheduled_for": "not-a-date"}], "leases": []}',
        encoding="utf-8",
    )

    result = CampaignTasksAPI(project).today(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert not result.successful
    assert "Invalid execution queue" in result.errors[0]
