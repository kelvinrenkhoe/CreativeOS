from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from models.action import Action
from services.action_repository import ActionRepository
from services.daily_brief import (
    DailyBriefService,
    MilestoneHealth,
    MilestoneProgress,
    MilestoneStatus,
)

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


def test_milestone_attention_includes_only_watch_and_at_risk() -> None:
    milestones = (
        MilestoneStatus("watch", date(2026, 8, 14), 6),
        MilestoneStatus("risk", date(2026, 8, 10), 2),
        MilestoneStatus("healthy", date(2026, 8, 30), 22),
    )
    progress = (
        MilestoneProgress("watch", 2, 1, 1, 0, 0),
        MilestoneProgress("risk", 3, 1, 0, 1, 1),
        MilestoneProgress("healthy", 2, 0, 2, 0, 0),
    )
    health = (
        MilestoneHealth("watch", "watch", "deadline is within seven days with incomplete work"),
        MilestoneHealth(
            "risk",
            "at-risk",
            "deadline is near with blocked or dependency-waiting work",
        ),
        MilestoneHealth(
            "healthy",
            "on-track",
            "remaining work is not currently deadline-constrained",
        ),
    )

    attention = DailyBriefService._milestone_attention(milestones, progress, health)

    assert [item.name for item in attention] == ["risk", "watch"]
    assert attention[0].blocked == 1
    assert attention[0].pending == 1
    assert attention[0].completed == 1
    assert attention[0].total == 3
    assert attention[0].reason == "deadline is near with blocked or dependency-waiting work"


def test_daily_brief_exposes_attention_from_existing_health(tmp_path: Path) -> None:
    repository = make_campaign(tmp_path)
    repository.save(
        Action("done", "Approve Artwork", status="completed", milestone="content_freeze")
    )
    repository.save(Action("blocked", "Fix Artwork", status="blocked", milestone="content_freeze"))
    repository.save(
        Action("waiting", "Package Assets", milestone="content_freeze", depends_on=("later",))
    )
    repository.save(Action("later", "Prepare Masters", milestone="launch"))

    brief = DailyBriefService(tmp_path, "kre", "no-lose-guard", "launch").build(date(2026, 8, 8))

    assert brief.milestone_attention
    content_freeze = brief.milestone_attention[0]
    assert content_freeze.name == "content_freeze"
    assert content_freeze.status == "at-risk"
    assert content_freeze.blocked == 1
    assert content_freeze.pending == 1


def test_today_command_renders_attention_summary(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("artwork", "Finalise Artwork", milestone="content_freeze"))
    repository.save(Action("blocked", "Fix Artwork", status="blocked", milestone="content_freeze"))
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["today", "--org", "kre", "--project", "no-lose-guard", "--campaign", "launch"],
    )

    assert result.exit_code == 0
    assert "Attention Required" in result.stdout
    assert "Content Freeze" in result.stdout
    assert "at-risk" in result.stdout
    assert "blocked" in result.stdout


def test_today_command_renders_clear_attention_state(tmp_path: Path, monkeypatch) -> None:
    make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["today", "--org", "kre", "--project", "no-lose-guard", "--campaign", "launch"],
    )

    assert result.exit_code == 0
    assert "Attention Required" in result.stdout
    assert "clear" in result.stdout
    assert "intervention" in result.stdout
