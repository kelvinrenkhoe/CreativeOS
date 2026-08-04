"""Tests for explicit local provider selection on campaign run."""

from types import SimpleNamespace

from typer.testing import CliRunner

from cli.main import app
from services.in_memory_provider import InMemoryProviderExecutionAdapter

runner = CliRunner()


class StubRunnerAPI:
    calls = []

    def __init__(self, project, *, adapters=(), worker_id):
        self.__class__.calls.append(
            SimpleNamespace(
                project=project,
                adapters=adapters,
                worker_id=worker_id,
            )
        )

    def advance(self, campaign_id):
        return SimpleNamespace(
            campaign_id=campaign_id,
            stage="ready",
            action="execution-completed",
            request_id="request-1",
            paused=False,
            errors=(),
        )


def _patch_runtime(monkeypatch) -> None:
    StubRunnerAPI.calls = []
    monkeypatch.setattr("cli.campaign.Project.discover", lambda: object())
    monkeypatch.setattr("cli.campaign.CampaignRunnerAPI", StubRunnerAPI)


def test_run_without_provider_remains_fail_closed(monkeypatch) -> None:
    _patch_runtime(monkeypatch)

    invocation = runner.invoke(app, ["campaign", "run", "campaign-1"])

    assert invocation.exit_code == 0
    assert StubRunnerAPI.calls[0].adapters == ()
    assert "None configured" in invocation.stdout


def test_run_with_in_memory_provider_injects_adapter(monkeypatch) -> None:
    _patch_runtime(monkeypatch)

    invocation = runner.invoke(
        app,
        ["campaign", "run", "campaign-1", "--provider", "in-memory"],
    )

    assert invocation.exit_code == 0
    adapters = StubRunnerAPI.calls[0].adapters
    assert len(adapters) == 1
    assert isinstance(adapters[0], InMemoryProviderExecutionAdapter)
    assert "in-memory" in invocation.stdout


def test_run_rejects_unknown_provider(monkeypatch) -> None:
    _patch_runtime(monkeypatch)

    invocation = runner.invoke(
        app,
        ["campaign", "run", "campaign-1", "--provider", "remote"],
    )

    assert invocation.exit_code == 1
    assert "unsupported execution provider: remote" in invocation.stdout
    assert StubRunnerAPI.calls == []


def test_run_help_describes_provider_option() -> None:
    invocation = runner.invoke(app, ["campaign", "run", "--help"])

    assert invocation.exit_code == 0
    assert "deterministic local execution" in invocation.stdout
