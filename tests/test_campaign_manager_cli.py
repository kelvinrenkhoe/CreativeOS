"""CLI tests for the deterministic campaign manager presentation layer."""

from datetime import UTC, date, datetime

from rich.console import Console
from typer.testing import CliRunner

from api.campaign_manager import CampaignManagerResult
from api.campaign_tasks import CampaignTask
from cli.main import app
from renderers.campaign_manager import CampaignManagerRenderer

runner = CliRunner()


def manager_result(**changes) -> CampaignManagerResult:
    """Return one deterministic manager result for CLI tests."""
    values = {
        "campaign": "No Lose Guard",
        "today": date(2026, 8, 4),
        "priority_action": "Prepare for milestone: Release day",
        "reason": "No overdue or due-today execution tasks remain.",
        "task": None,
        "current_phase": "Promotion",
        "next_milestone": "Release day",
        "warnings": (),
        "errors": (),
    }
    values.update(changes)
    return CampaignManagerResult(**values)


def install_manager(monkeypatch, result: CampaignManagerResult) -> None:
    """Replace project discovery and manager API with deterministic doubles."""
    import cli.campaign_manager as command

    class StubAPI:
        def __init__(self, _project) -> None:
            pass

        def today(self, campaign_name: str):
            assert campaign_name == result.campaign
            return result

    monkeypatch.setattr(command.Project, "discover", lambda: object())
    monkeypatch.setattr(command, "CampaignManagerAPI", StubAPI)


def test_today_command_renders_priority_action(monkeypatch) -> None:
    result = manager_result()
    install_manager(monkeypatch, result)

    invocation = runner.invoke(
        app,
        ["campaign", "today", "No Lose Guard"],
        terminal_width=160,
    )

    assert invocation.exit_code == 0
    output = " ".join(invocation.stdout.split())
    assert "CreativeOS Campaign Today" in output
    assert "No Lose Guard" in output
    assert "Promotion" in output
    assert "Prepare for milestone: Release day" in output
    assert "No overdue or due-today execution tasks remain." in output


def test_today_command_renders_related_task(monkeypatch) -> None:
    task = CampaignTask(
        request_id="request-teaser",
        asset_id="teaser-video",
        media_type="video",
        provider="local",
        scheduled_for=datetime(2026, 8, 4, 9, tzinfo=UTC),
        status="scheduled",
        priority=20,
    )
    result = manager_result(
        priority_action="Complete today's task: teaser-video",
        reason="This is the highest-priority task scheduled for today.",
        task=task,
    )
    install_manager(monkeypatch, result)

    invocation = runner.invoke(app, ["campaign", "today", "No Lose Guard"])

    assert invocation.exit_code == 0
    assert "Related Task" in invocation.stdout
    assert "request-teaser" in invocation.stdout
    assert "teaser-video" in invocation.stdout
    assert "local" in invocation.stdout


def test_today_command_renders_warnings(monkeypatch) -> None:
    result = manager_result(warnings=("Queue warning",))
    install_manager(monkeypatch, result)

    invocation = runner.invoke(app, ["campaign", "today", "No Lose Guard"])

    assert invocation.exit_code == 0
    assert "Warnings" in invocation.stdout
    assert "Queue warning" in invocation.stdout


def test_today_command_renders_errors_and_exits_one(monkeypatch) -> None:
    result = manager_result(
        priority_action=None,
        reason=None,
        errors=("Campaign workspace not found",),
    )
    install_manager(monkeypatch, result)

    invocation = runner.invoke(app, ["campaign", "today", "No Lose Guard"])

    assert invocation.exit_code == 1
    assert "Errors" in invocation.stdout
    assert "Campaign workspace not found" in invocation.stdout


def test_today_command_is_registered() -> None:
    invocation = runner.invoke(app, ["campaign", "today", "--help"])

    assert invocation.exit_code == 0
    assert "highest-priority campaign action" in invocation.stdout


def test_renderer_output_is_deterministic() -> None:
    result = manager_result()
    first = Console(record=True, width=160)
    second = Console(record=True, width=160)

    first.print(CampaignManagerRenderer().render(result))
    second.print(CampaignManagerRenderer().render(result))

    assert first.export_text() == second.export_text()
