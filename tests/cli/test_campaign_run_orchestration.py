"""Tests for bounded campaign orchestration through the CLI."""

from types import SimpleNamespace

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def runtime_result(
    *,
    stage="ready",
    action="execution-completed",
    request_id="request-1",
    paused=False,
    uncertain=False,
    errors=(),
):
    return SimpleNamespace(
        campaign_id="campaign-1",
        stage=stage,
        action=action,
        request_id=request_id,
        paused=paused,
        uncertain=uncertain,
        errors=errors,
    )


class SequencedRunnerAPI:
    results = []
    calls = []

    def __init__(self, project, *, worker_id, adapters=()):
        self.project = project
        self.worker_id = worker_id
        self.adapters = adapters

    def advance(self, campaign_id, *, now=None):
        self.__class__.calls.append((campaign_id, now))
        if not self.__class__.results:
            raise AssertionError("runner called more times than expected")
        return self.__class__.results.pop(0)


def _patch_runtime(monkeypatch, *results) -> None:
    SequencedRunnerAPI.results = list(results)
    SequencedRunnerAPI.calls = []
    monkeypatch.setattr("cli.campaign.Project.discover", lambda: object())
    monkeypatch.setattr("cli.campaign.CampaignRunnerAPI", SequencedRunnerAPI)


def test_default_policy_advances_once(monkeypatch) -> None:
    _patch_runtime(monkeypatch, runtime_result())

    invocation = runner.invoke(app, ["campaign", "run", "campaign-1"])

    assert invocation.exit_code == 0
    assert len(SequencedRunnerAPI.calls) == 1
    assert "once" in invocation.stdout
    assert "Steps" in invocation.stdout


def test_until_complete_runs_multiple_steps(monkeypatch) -> None:
    _patch_runtime(
        monkeypatch,
        runtime_result(action="queued", request_id="request-1"),
        runtime_result(
            stage="completed",
            action="campaign-finished",
            request_id=None,
        ),
    )

    invocation = runner.invoke(
        app,
        ["campaign", "run", "campaign-1", "--until-complete"],
    )

    assert invocation.exit_code == 0
    assert len(SequencedRunnerAPI.calls) == 2
    assert "until-complete" in invocation.stdout
    assert "campaign-finished" in invocation.stdout
    assert "Yes" in invocation.stdout


def test_until_blocked_reports_pause_without_error_exit(monkeypatch) -> None:
    _patch_runtime(
        monkeypatch,
        runtime_result(action="queued"),
        runtime_result(action="awaiting-review", paused=True),
    )

    invocation = runner.invoke(
        app,
        ["campaign", "run", "campaign-1", "--until-blocked"],
    )

    assert invocation.exit_code == 0
    assert "campaign-blocked" in invocation.stdout
    assert "Paused" in invocation.stdout


def test_conflicting_policy_flags_are_rejected(monkeypatch) -> None:
    _patch_runtime(monkeypatch)

    invocation = runner.invoke(
        app,
        [
            "campaign",
            "run",
            "campaign-1",
            "--once",
            "--until-complete",
        ],
    )

    assert invocation.exit_code == 1
    assert "choose only one" in invocation.stdout
    assert SequencedRunnerAPI.calls == []


def test_uncertain_result_uses_failure_exit_code(monkeypatch) -> None:
    _patch_runtime(monkeypatch, runtime_result(action="provider-submitted", uncertain=True))

    invocation = runner.invoke(app, ["campaign", "run", "campaign-1"])

    assert invocation.exit_code == 1
    assert "Uncertain" in invocation.stdout
    assert "campaign-blocked" in invocation.stdout


def test_help_lists_orchestration_options() -> None:
    invocation = runner.invoke(app, ["campaign", "run", "--help"])

    assert invocation.exit_code == 0
    assert "Advance exactly one safe action." in invocation.stdout
    assert "Continue until completion" in invocation.stdout
    assert "Continue toward completion" in invocation.stdout
    assert "Maximum safe actions" in invocation.stdout
