from datetime import date, timedelta
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from models.action import Action
from services.action_repository import ActionRepository
from services.daily_brief import DailyBriefService

runner = CliRunner()


def make_campaign(tmp_path: Path, *, milestones: str = "") -> ActionRepository:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n",
        encoding="utf-8",
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard"
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\n",
        encoding="utf-8",
    )
    campaign_yaml = "id: launch\nname: Launch\nstatus: active\nobjective: Release campaign\n"
    if milestones:
        campaign_yaml += f"milestones:\n{milestones}"
    (campaign_root / "campaign.yaml").write_text(campaign_yaml, encoding="utf-8")
    return ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")


def test_daily_brief_is_empty_for_campaign_without_actions(tmp_path: Path) -> None:
    make_campaign(tmp_path)

    brief = DailyBriefService(tmp_path, "kre", "no-lose-guard", "launch").build(date(2026, 8, 7))

    assert brief.campaign.name == "Launch"
    assert brief.today == ()
    assert brief.overdue == ()
    assert brief.blocked == ()
    assert brief.next_actions == ()
    assert brief.milestones == ()
    assert brief.recommended_next is None
    assert brief.progress.total == 0


def test_daily_brief_composes_execution_state(tmp_path: Path) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("overdue", "Send Pitch", due_date=date(2026, 8, 6), priority="high"))
    repository.save(Action("today", "Publish Reel", due_date=date(2026, 8, 7), priority="critical"))
    repository.save(Action("blocked", "Upload Canvas", due_date=date(2026, 8, 7), status="blocked"))

    brief = DailyBriefService(tmp_path, "kre", "no-lose-guard", "launch").build(date(2026, 8, 7))

    assert [action.action_id for action in brief.overdue] == ["overdue"]
    assert {action.action_id for action in brief.today} == {"today", "blocked"}
    assert [action.action_id for action in brief.blocked] == ["blocked"]
    assert brief.recommended_next is not None
    assert brief.recommended_next.action_id == "overdue"
    assert brief.progress.total == 3


def test_daily_brief_orders_and_classifies_campaign_milestones(tmp_path: Path) -> None:
    make_campaign(
        tmp_path,
        milestones=("  launch: 2026-08-14\n  content_freeze: 2026-08-08\n  briefing: 2026-08-06\n"),
    )

    brief = DailyBriefService(tmp_path, "kre", "no-lose-guard", "launch").build(date(2026, 8, 8))

    assert [milestone.name for milestone in brief.milestones] == [
        "briefing",
        "content_freeze",
        "launch",
    ]
    assert [milestone.days_from_brief for milestone in brief.milestones] == [-2, 0, 6]
    assert brief.milestones[0].is_overdue
    assert brief.milestones[1].is_today
    assert not brief.milestones[2].is_overdue


def test_today_command_renders_daily_brief(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(
        tmp_path,
        milestones="  content_freeze: 2026-08-08\n  launch: 2026-08-15\n",
    )
    repository.save(Action("publish-reel", "Publish Reel", due_date=date.today()))
    repository.save(Action("old-pitch", "Old Pitch", due_date=date.today() - timedelta(days=1)))
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "today",
            "--org",
            "kre",
            "--project",
            "no-lose-guard",
            "--campaign",
            "launch",
        ],
    )

    assert result.exit_code == 0
    assert "CreativeOS Daily Brief" in result.stdout
    assert "Campaign Milestones" in result.stdout
    assert "Content Freeze" in result.stdout
    assert "Today" in result.stdout
    assert "Launch" in result.stdout
    assert "in 7 days" in result.stdout
    assert "Publish Reel" in result.stdout
    assert "Old Pitch" in result.stdout
    assert "Recommended Next Step" in result.stdout


def test_today_command_rejects_invalid_context(tmp_path: Path, monkeypatch) -> None:
    make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "today",
            "--org",
            "kre",
            "--project",
            "../escape",
            "--campaign",
            "launch",
        ],
    )

    assert result.exit_code == 1
    assert "Error:" in result.stdout


def test_existing_top_level_next_command_remains_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "today" in result.stdout
    assert "next" in result.stdout
