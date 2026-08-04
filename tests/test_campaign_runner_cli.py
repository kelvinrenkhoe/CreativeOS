"""CLI tests for the API-backed campaign runner command."""

from typer.testing import CliRunner

from api.campaign_runner import CampaignRunnerResult
from cli.main import app

runner = CliRunner()


def install_runner(monkeypatch, result: CampaignRunnerResult, calls: list[tuple]) -> None:
    """Replace project discovery and runner API with deterministic doubles."""
    import cli.campaign as command

    project = object()

    class StubAPI:
        def __init__(self, supplied_project, *, worker_id: str) -> None:
            calls.append(("init", supplied_project, worker_id))

        def advance(self, campaign_id: str) -> CampaignRunnerResult:
            calls.append(("advance", campaign_id))
            return result

    monkeypatch.setattr(command.Project, "discover", lambda: project)
    monkeypatch.setattr(command, "CampaignRunnerAPI", StubAPI)


def test_run_command_delegates_to_runner_api(monkeypatch) -> None:
    calls: list[tuple] = []
    install_runner(
        monkeypatch,
        CampaignRunnerResult(
            campaign_id="campaign-1",
            stage="review",
            action="awaiting-review",
            request_id="request-1",
            paused=True,
        ),
        calls,
    )

    result = runner.invoke(app, ["campaign", "run", "campaign-1"])

    assert result.exit_code == 0
    assert calls[0][0] == "init"
    assert calls[0][2] == "creativeos-cli"
    assert calls[1] == ("advance", "campaign-1")


def test_run_command_renders_structured_result(monkeypatch) -> None:
    calls: list[tuple] = []
    install_runner(
        monkeypatch,
        CampaignRunnerResult(
            campaign_id="campaign-1",
            stage="in-production",
            action="queued",
            request_id="request-7",
            paused=False,
        ),
        calls,
    )

    result = runner.invoke(
        app,
        ["campaign", "run", "campaign-1"],
        terminal_width=160,
    )
    output = " ".join(result.stdout.split())

    assert result.exit_code == 0
    assert "Campaign Runtime Action" in output
    assert "campaign-1" in output
    assert "in-production" in output
    assert "queued" in output
    assert "request-7" in output
    assert "No" in output


def test_run_command_renders_api_errors_and_exits_one(monkeypatch) -> None:
    calls: list[tuple] = []
    install_runner(
        monkeypatch,
        CampaignRunnerResult(
            campaign_id="campaign-1",
            errors=("runtime action is uncertain", "reconcile before retrying"),
        ),
        calls,
    )

    result = runner.invoke(app, ["campaign", "run", "campaign-1"])

    assert result.exit_code == 1
    assert "runtime action is uncertain" in result.stdout
    assert "reconcile before retrying" in result.stdout
    assert "Campaign Runtime Action" not in result.stdout


def test_run_command_handles_project_discovery_failure(monkeypatch) -> None:
    import cli.campaign as command

    def fail():
        raise command.ConfigurationError("workspace configuration missing")

    monkeypatch.setattr(command.Project, "discover", fail)

    result = runner.invoke(app, ["campaign", "run", "campaign-1"])

    assert result.exit_code == 1
    assert "workspace configuration missing" in result.stdout
