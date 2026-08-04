"""CLI tests for the API-backed campaign runtime command."""

from types import SimpleNamespace

from typer.testing import CliRunner

from api.campaign_runner import CampaignRunnerResult
from cli.campaign import app

runner = CliRunner()


def install_runner(monkeypatch, result: CampaignRunnerResult, calls: list[tuple]) -> None:
    """Replace project discovery and runner API with deterministic doubles."""
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root="/workspace"),
    )

    class StubAPI:
        def __init__(self, project, *, worker_id: str) -> None:
            calls.append((project, worker_id))

        def advance(self, campaign_id: str) -> CampaignRunnerResult:
            calls.append((campaign_id,))
            return result

    monkeypatch.setattr("cli.campaign.CampaignRunnerAPI", StubAPI)


def test_run_delegates_exactly_once_and_renders_result(monkeypatch) -> None:
    calls: list[tuple] = []
    install_runner(
        monkeypatch,
        CampaignRunnerResult(
            campaign_id="no-lose-guard-launch",
            stage="in-production",
            action="production-started",
            paused=False,
        ),
        calls,
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 0
    assert calls[0][1] == "creativeos-cli"
    assert calls[1] == ("no-lose-guard-launch",)
    assert "Campaign Runtime Action" in result.stdout
    assert "in-production" in result.stdout
    assert "production-started" in result.stdout
    assert "No" in result.stdout


def test_run_renders_paused_result(monkeypatch) -> None:
    calls: list[tuple] = []
    install_runner(
        monkeypatch,
        CampaignRunnerResult(
            campaign_id="no-lose-guard-launch",
            stage="ready",
            action="awaiting-publication",
            paused=True,
        ),
        calls,
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 0
    assert "awaiting-publication" in result.stdout
    assert "Yes" in result.stdout


def test_run_renders_structured_errors_and_exits_one(monkeypatch) -> None:
    calls: list[tuple] = []
    install_runner(
        monkeypatch,
        CampaignRunnerResult(
            campaign_id="no-lose-guard-launch",
            errors=("invalid queue snapshot", "runtime blocked"),
        ),
        calls,
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "invalid queue snapshot" in result.stdout
    assert "runtime blocked" in result.stdout


def test_run_returns_non_zero_when_project_discovery_fails(monkeypatch) -> None:
    from core.config import ConfigurationError

    def fail_discovery():
        raise ConfigurationError("workspace not configured")

    monkeypatch.setattr("cli.campaign.Project.discover", fail_discovery)

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 1
    assert "workspace not configured" in result.stdout
