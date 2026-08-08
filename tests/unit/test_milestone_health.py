from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from models.action import Action
from services.action_repository import ActionRepository
from services.daily_brief import DailyBriefService, MilestoneProgress, MilestoneStatus

runner = CliRunner()


def make_campaign(tmp_path: Path) -> ActionRepository:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n", encoding="utf-8"
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard"
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\n", encoding="utf-8"
    )
    (campaign_root / "campaign.yaml").write_text(
        "id: launch\n"
        "name: Launch\n"
        "status: active\n"
        "milestones:\n"
        "  content_freeze: 2026-08-10\n"
        "  launch: 2026-08-15\n",
        encoding="utf-8",
    )
    return ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")


def test_milestone_health_covers_all_states() -> None:
    milestones = (
        MilestoneStatus("untracked", date(2026, 8, 20), 12),
        MilestoneStatus("complete", date(2026, 8, 1), -7),
        MilestoneStatus("overdue", date(2026, 8, 7), -1),
        MilestoneStatus("near", date(2026, 8, 10), 2),
        MilestoneStatus("upcoming", date(2026, 8, 14), 6),
        MilestoneStatus("blocked_later", date(2026, 8, 30), 22),
        MilestoneStatus("healthy", date(2026, 8, 30), 22),
    )
    progress = (
        MilestoneProgress("untracked", 0, 0, 0, 0, 0),
        MilestoneProgress("complete", 2, 2, 0, 0, 0),
        MilestoneProgress("overdue", 2, 1, 1, 0, 0),
        MilestoneProgress("near", 3, 1, 1, 1, 0),
        MilestoneProgress("upcoming", 2, 1, 1, 0, 0),
        MilestoneProgress("blocked_later", 2, 0, 1, 0, 1),
        MilestoneProgress("healthy", 2, 0, 2, 0, 0),
    )

    health = DailyBriefService._milestone_health(milestones, progress)

    assert [item.status for item in health] == [
        "untracked",
        "complete",
        "at-risk",
        "at-risk",
        "watch",
        "watch",
        "on-track",
    ]


def test_daily_brief_exposes_focus_milestone_health(tmp_path: Path) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("artwork", "Finalise Artwork", milestone="content_freeze"))
    repository.save(
        Action("blocked", "Fix Artwork", status="blocked", milestone="content_freeze")
    )

    brief = DailyBriefService(tmp_path, "kre", "no-lose-guard", "launch").build(date(2026, 8, 8))

    assert brief.focus_milestone is not None
    assert brief.focus_milestone.name == "content_freeze"
    assert brief.focus_milestone_health is not None
    assert brief.focus_milestone_health.status == "at-risk"


def test_today_command_renders_milestone_health(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("artwork", "Finalise Artwork", milestone="content_freeze"))
    repository.save(
        Action("blocked", "Fix Artwork", status="blocked", milestone="content_freeze")
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["today", "--org", "kre", "--project", "no-lose-guard", "--campaign", "launch"],
    )

    assert result.exit_code == 0
    assert "Health" in result.stdout
    assert "at-risk" in result.stdout
    assert "Milestone Focus" in result.stdout
