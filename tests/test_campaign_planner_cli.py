"""CLI tests for the deterministic campaign planner presentation layer."""

from datetime import UTC, date, datetime

from rich.console import Console
from typer.testing import CliRunner

from api.campaign_planner import CampaignPlanResult, DailyPlan
from api.campaign_tasks import CampaignTask
from cli.main import app
from renderers.campaign_planner import CampaignPlannerRenderer

runner = CliRunner()


def planner_result(**changes) -> CampaignPlanResult:
    """Return one deterministic planner result for CLI tests."""
    values = {
        "campaign": "No Lose Guard",
        "start": date(2026, 8, 4),
        "end": date(2026, 8, 10),
        "daily_plans": (
            DailyPlan(
                date=date(2026, 8, 4),
                milestone="Spotify pitch",
                priority="milestone",
            ),
        ),
        "warnings": (),
        "errors": (),
    }
    values.update(changes)
    return CampaignPlanResult(**values)


def install_planner(monkeypatch, result: CampaignPlanResult, calls: list[int]) -> None:
    """Replace project discovery and planner API with deterministic doubles."""
    import cli.campaign_planner as command

    class StubAPI:
        def __init__(self, _project) -> None:
            pass

        def plan(self, campaign_name: str, *, days: int = 7):
            assert campaign_name == result.campaign
            calls.append(days)
            return result

    monkeypatch.setattr(command.Project, "discover", lambda: object())
    monkeypatch.setattr(command, "CampaignPlannerAPI", StubAPI)


def test_plan_command_uses_default_seven_days(monkeypatch) -> None:
    result = planner_result()
    calls: list[int] = []
    install_planner(monkeypatch, result, calls)

    invocation = runner.invoke(
        app,
        ["campaign", "plan", "No Lose Guard"],
        terminal_width=180,
    )

    assert invocation.exit_code == 0
    assert calls == [7]
    output = " ".join(invocation.stdout.split())
    assert "CreativeOS Campaign Plan" in output
    assert "No Lose Guard" in output
    assert "Spotify pitch" in output
    assert "milestone" in output


def test_plan_command_passes_custom_days(monkeypatch) -> None:
    result = planner_result(end=date(2026, 8, 6))
    calls: list[int] = []
    install_planner(monkeypatch, result, calls)

    invocation = runner.invoke(
        app,
        ["campaign", "plan", "No Lose Guard", "--days", "3"],
    )

    assert invocation.exit_code == 0
    assert calls == [3]
    assert "2026-08-06" in invocation.stdout


def test_plan_command_renders_tasks_and_effort(monkeypatch) -> None:
    task = CampaignTask(
        request_id="request-teaser",
        asset_id="teaser-video",
        media_type="video",
        provider="local",
        scheduled_for=datetime(2026, 8, 4, 9, tzinfo=UTC),
        status="scheduled",
        priority=20,
    )
    result = planner_result(
        daily_plans=(
            DailyPlan(
                date=date(2026, 8, 4),
                tasks=(task,),
                priority="high",
                estimated_minutes=30,
            ),
        )
    )
    calls: list[int] = []
    install_planner(monkeypatch, result, calls)

    invocation = runner.invoke(app, ["campaign", "plan", "No Lose Guard"])

    assert invocation.exit_code == 0
    assert "teaser-video" in invocation.stdout
    assert "30 minutes" in invocation.stdout
    assert "priority 20" in invocation.stdout


def test_plan_command_renders_warnings(monkeypatch) -> None:
    result = planner_result(warnings=("Queue warning",))
    calls: list[int] = []
    install_planner(monkeypatch, result, calls)

    invocation = runner.invoke(app, ["campaign", "plan", "No Lose Guard"])

    assert invocation.exit_code == 0
    assert "Warnings" in invocation.stdout
    assert "Queue warning" in invocation.stdout


def test_plan_command_renders_errors_and_exits_one(monkeypatch) -> None:
    result = planner_result(daily_plans=(), errors=("Campaign workspace not found",))
    calls: list[int] = []
    install_planner(monkeypatch, result, calls)

    invocation = runner.invoke(app, ["campaign", "plan", "No Lose Guard"])

    assert invocation.exit_code == 1
    assert "Errors" in invocation.stdout
    assert "Campaign workspace not found" in invocation.stdout


def test_plan_command_rejects_invalid_days() -> None:
    invocation = runner.invoke(
        app,
        ["campaign", "plan", "No Lose Guard", "--days", "0"],
    )

    assert invocation.exit_code == 2


def test_plan_command_is_registered() -> None:
    invocation = runner.invoke(app, ["campaign", "plan", "--help"])

    assert invocation.exit_code == 0
    assert "multi-day campaign execution plan" in invocation.stdout
    assert "Number of days to plan." in invocation.stdout


def test_renderer_output_is_deterministic() -> None:
    result = planner_result()
    first = Console(record=True, width=180)
    second = Console(record=True, width=180)

    first.print(CampaignPlannerRenderer().render(result))
    second.print(CampaignPlannerRenderer().render(result))

    assert first.export_text() == second.export_text()
