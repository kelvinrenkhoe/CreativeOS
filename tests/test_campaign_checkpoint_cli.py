"""Tests for campaign runtime checkpoint inspection and reconciliation."""

from datetime import UTC, datetime
from types import SimpleNamespace

from typer.testing import CliRunner

from api.campaign_runner import CHECKPOINTS_PATH
from cli import campaign as campaign_cli
from cli.main import app
from services.runtime_checkpoints import JsonRuntimeCheckpointStore

runner = CliRunner()
NOW = datetime(2026, 8, 5, 9, 0, tzinfo=UTC)


def install_project(monkeypatch, tmp_path):
    project = SimpleNamespace(root=tmp_path)
    monkeypatch.setattr(campaign_cli.Project, "discover", lambda: project)
    return JsonRuntimeCheckpointStore(tmp_path / CHECKPOINTS_PATH)


def test_status_reports_missing_campaign_checkpoints(monkeypatch, tmp_path) -> None:
    install_project(monkeypatch, tmp_path)

    result = runner.invoke(app, ["campaign", "checkpoint", "status", "campaign-1"])

    assert result.exit_code == 0
    assert "No runtime checkpoints found for campaign-1" in result.stdout


def test_status_renders_campaign_checkpoint(monkeypatch, tmp_path) -> None:
    store = install_project(monkeypatch, tmp_path)
    store.begin(campaign_id="campaign-1", action_key="publish", now=NOW)

    result = runner.invoke(app, ["campaign", "checkpoint", "status", "campaign-1"])

    assert result.exit_code == 0
    assert "Campaign Runtime Checkpoints" in result.stdout
    assert "publish" in result.stdout
    assert "started" in result.stdout


def test_reconcile_confirm_not_completed_marks_checkpoint_retryable(
    monkeypatch,
    tmp_path,
) -> None:
    store = install_project(monkeypatch, tmp_path)
    checkpoint, _ = store.begin(
        campaign_id="campaign-1",
        action_key="publish",
        now=NOW,
    )
    store.mark_uncertain(checkpoint, now=NOW)

    result = runner.invoke(
        app,
        [
            "campaign",
            "checkpoint",
            "reconcile",
            "campaign-1",
            "--decision",
            "confirm-not-completed",
        ],
    )

    assert result.exit_code == 0
    assert "reconciled as retryable" in result.stdout
    assert store.load()[0].status == "retryable"


def test_reconcile_confirm_completed_requires_verified_outcome(
    monkeypatch,
    tmp_path,
) -> None:
    store = install_project(monkeypatch, tmp_path)
    checkpoint, _ = store.begin(
        campaign_id="campaign-1",
        action_key="publish",
        now=NOW,
    )
    store.mark_uncertain(checkpoint, now=NOW)

    result = runner.invoke(
        app,
        [
            "campaign",
            "checkpoint",
            "reconcile",
            "campaign-1",
            "--decision",
            "confirm-completed",
        ],
    )

    assert result.exit_code == 1
    assert "requires a verified persisted outcome" in result.stdout


def test_reconcile_confirm_completed_records_verified_outcome(
    monkeypatch,
    tmp_path,
) -> None:
    store = install_project(monkeypatch, tmp_path)
    checkpoint, _ = store.begin(
        campaign_id="campaign-1",
        action_key="publish",
        now=NOW,
    )
    store.mark_uncertain(checkpoint, now=NOW)

    result = runner.invoke(
        app,
        [
            "campaign",
            "checkpoint",
            "reconcile",
            "campaign-1",
            "--decision",
            "confirm-completed",
            "--result-action",
            "published",
            "--resulting-stage",
            "published",
            "--request-id",
            "request-1",
        ],
    )

    assert result.exit_code == 0
    stored = store.load()[0]
    assert stored.status == "completed"
    assert stored.result_action == "published"
    assert stored.resulting_stage == "published"
    assert stored.request_id == "request-1"
