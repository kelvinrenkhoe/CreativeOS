from datetime import date, timedelta
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from models.action import Action
from services.action_repository import ActionRepository

runner = CliRunner()


def make_campaign(tmp_path: Path) -> ActionRepository:
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
    (campaign_root / "campaign.yaml").write_text(
        "id: launch\nname: Launch\n",
        encoding="utf-8",
    )
    return ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")


def context_args(command: str) -> list[str]:
    return [
        "execution",
        command,
        "--org",
        "kre",
        "--project",
        "no-lose-guard",
        "--campaign",
        "launch",
    ]


def test_execution_today_shows_context_due_work_and_progress(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("publish-reel", "Publish Reel", due_date=date.today()))
    repository.save(
        Action("old-pitch", "Old Pitch", due_date=date.today() - timedelta(days=1))
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, context_args("today"))

    assert result.exit_code == 0
    assert "kre / no-lose-guard / launch" in result.stdout
    assert "Publish Reel" in result.stdout
    assert "Old Pitch" in result.stdout
    assert "Progress: 0/2" in result.stdout


def test_execution_next_returns_highest_value_ready_work(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("normal", "Normal", priority="normal"))
    repository.save(Action("critical", "Critical", priority="critical"))
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, [*context_args("next"), "--limit", "1"])

    assert result.exit_code == 0
    assert "Critical" in result.stdout
    assert "Normal" not in result.stdout


def test_execution_ready_excludes_dependency_blocked_work(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    repository.save(Action("render", "Render Video"))
    repository.save(Action("publish", "Publish Video", depends_on=("render",)))
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, context_args("ready"))

    assert result.exit_code == 0
    assert "Render Video" in result.stdout
    assert "Publish Video" not in result.stdout


def test_execution_reports_invalid_context(tmp_path: Path, monkeypatch) -> None:
    make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "execution",
            "ready",
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


def test_top_level_next_command_is_preserved() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "execution" in result.stdout
    assert "next" in result.stdout
