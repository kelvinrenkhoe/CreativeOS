"""CLI tests for the campaign summary dashboard presentation layer."""

from datetime import date

from rich.console import Console
from typer.testing import CliRunner

from api.campaign_dashboard import CampaignDashboardResult
from cli.main import app
from renderers.campaign_dashboard import CampaignDashboardRenderer

runner = CliRunner()


def dashboard_result(**changes) -> CampaignDashboardResult:
    """Return a deterministic dashboard result for CLI tests."""
    values = {
        "campaign": "No Lose Guard",
        "today": date(2026, 8, 4),
        "readiness_score": 86,
        "readiness_label": "ready",
        "quality_score": 91,
        "current_phase": "Promotion",
        "completion_percent": 64,
        "overdue_task_count": 2,
        "due_today_count": 3,
        "next_milestone": "Visualizer Release",
        "recommendation_count": 5,
        "warning_count": 0,
        "error_count": 0,
        "warnings": (),
        "errors": (),
    }
    values.update(changes)
    return CampaignDashboardResult(**values)


def install_dashboard(monkeypatch, result: CampaignDashboardResult) -> None:
    """Replace project discovery and dashboard API with deterministic doubles."""
    import cli.campaign_dashboard as command

    class StubAPI:
        def __init__(self, _project) -> None:
            pass

        def summary(self, campaign_name: str):
            assert campaign_name == result.campaign
            return result

    monkeypatch.setattr(command.Project, "discover", lambda: object())
    monkeypatch.setattr(command, "CampaignDashboardAPI", StubAPI)


def test_dashboard_command_renders_healthy_summary(monkeypatch) -> None:
    result = dashboard_result()
    install_dashboard(monkeypatch, result)

    invocation = runner.invoke(
        app,
        ["campaign", "dashboard", "No Lose Guard"],
        terminal_width=160,
    )

    assert invocation.exit_code == 0
    output = " ".join(invocation.stdout.split())
    assert "CreativeOS Campaign Dashboard" in output
    assert "No Lose Guard" in output
    assert "ready (86)" in output
    assert "Quality Score 91" in output
    assert "Promotion" in output
    assert "64%" in output
    assert "Visualizer Release" in output


def test_dashboard_command_renders_warnings(monkeypatch) -> None:
    result = dashboard_result(
        warning_count=2,
        warnings=("Missing artwork", "No radio list"),
    )
    install_dashboard(monkeypatch, result)

    invocation = runner.invoke(app, ["campaign", "dashboard", "No Lose Guard"])

    assert invocation.exit_code == 0
    assert "Warnings" in invocation.stdout
    assert "Missing artwork" in invocation.stdout
    assert "No radio list" in invocation.stdout


def test_dashboard_command_renders_errors_and_exits_one(monkeypatch) -> None:
    result = dashboard_result(
        error_count=1,
        errors=("Campaign workspace not found",),
    )
    install_dashboard(monkeypatch, result)

    invocation = runner.invoke(app, ["campaign", "dashboard", "No Lose Guard"])

    assert invocation.exit_code == 1
    assert "Errors" in invocation.stdout
    assert "Campaign workspace not found" in invocation.stdout


def test_dashboard_command_renders_empty_campaign(monkeypatch) -> None:
    result = dashboard_result(
        readiness_score=0,
        readiness_label="needs-attention",
        quality_score=0,
        current_phase="Planning",
        completion_percent=0,
        overdue_task_count=0,
        due_today_count=0,
        next_milestone=None,
        recommendation_count=0,
    )
    install_dashboard(monkeypatch, result)

    invocation = runner.invoke(app, ["campaign", "dashboard", "No Lose Guard"])

    assert invocation.exit_code == 0
    output = " ".join(invocation.stdout.split())
    assert "needs-attention (0)" in output
    assert "Planning" in output
    assert "Next Milestone None" in output


def test_dashboard_command_is_registered() -> None:
    invocation = runner.invoke(app, ["campaign", "dashboard", "--help"])

    assert invocation.exit_code == 0
    assert "aggregated campaign dashboard" in invocation.stdout


def test_renderer_formats_counts_and_sections() -> None:
    result = dashboard_result(
        warning_count=1,
        error_count=1,
        warnings=("Warning one",),
        errors=("Error one",),
    )
    console = Console(record=True, width=160)

    console.print(CampaignDashboardRenderer().render(result))
    output = " ".join(console.export_text().split())

    assert "Overdue Tasks 2" in output
    assert "Due Today 3" in output
    assert "Recommendations 5" in output
    assert "Warning one" in output
    assert "Error one" in output


def test_renderer_output_is_deterministic() -> None:
    result = dashboard_result()
    first = Console(record=True, width=160)
    second = Console(record=True, width=160)

    first.print(CampaignDashboardRenderer().render(result))
    second.print(CampaignDashboardRenderer().render(result))

    assert first.export_text() == second.export_text()
