"""Tests for background campaign worker CLI commands."""

from dataclasses import dataclass

from typer.testing import CliRunner

from api.campaign_orchestrator import CampaignOrchestrationResult
from cli.main import app
from services.campaign_worker import (
    CampaignWorkerResult,
    CampaignWorkerStatus,
)

runner = CliRunner()


@dataclass(frozen=True)
class StubPlan:
    work_name: str


@dataclass(frozen=True)
class StubRun:
    campaign_id: str
    stage: str
    plan: StubPlan


class StubWorker:
    def __init__(self, *, result=None, status=None) -> None:
        self.result = result
        self.status_result = status

    def run_once(self):
        return self.result

    def status(self):
        return self.status_result


def test_run_once_reports_idle_worker(monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.worker._worker",
        lambda provider, max_steps: StubWorker(result=CampaignWorkerResult()),
    )

    result = runner.invoke(app, ["worker", "run-once"])

    assert result.exit_code == 0
    assert "worker is idle" in result.stdout


def test_run_once_renders_successful_orchestration(monkeypatch) -> None:
    orchestration = CampaignOrchestrationResult(
        "campaign-1",
        "until-blocked",
        steps=3,
        paused=True,
    )
    monkeypatch.setattr(
        "cli.worker._worker",
        lambda provider, max_steps: StubWorker(
            result=CampaignWorkerResult("campaign-1", orchestration)
        ),
    )

    result = runner.invoke(app, ["worker", "run-once", "--max-steps", "5"])

    assert result.exit_code == 0
    assert "Campaign Worker Run" in result.stdout
    assert "campaign-1" in result.stdout
    assert "3" in result.stdout


def test_run_once_exits_one_for_orchestration_errors(monkeypatch) -> None:
    orchestration = CampaignOrchestrationResult(
        "campaign-1",
        "until-blocked",
        errors=("provider unavailable",),
    )
    monkeypatch.setattr(
        "cli.worker._worker",
        lambda provider, max_steps: StubWorker(
            result=CampaignWorkerResult("campaign-1", orchestration)
        ),
    )

    result = runner.invoke(app, ["worker", "run-once"])

    assert result.exit_code == 1
    assert "provider unavailable" in result.stdout


def test_status_lists_pending_campaigns(monkeypatch) -> None:
    pending = StubRun("campaign-1", "brief", StubPlan("No Lose Guard"))
    worker = StubWorker(status=CampaignWorkerStatus((pending,), ()))
    monkeypatch.setattr("cli.worker.campaign_cli.Project.discover", lambda: object())
    monkeypatch.setattr(
        "cli.worker.CampaignWorkerAPI.for_project",
        lambda project: worker,
    )

    result = runner.invoke(app, ["worker", "status"])

    assert result.exit_code == 0
    assert "work available" in result.stdout
    assert "campaign-1" in result.stdout
    assert "No Lose Guard" in result.stdout
