"""Tests for the persisted campaign orchestration history command."""

from types import SimpleNamespace

from typer.testing import CliRunner

from cli.main import app
from services.campaign_orchestration_events import JsonOrchestrationEventStore

runner = CliRunner()


def install_project(monkeypatch, root) -> None:
    import cli.campaign as campaign_cli

    monkeypatch.setattr(
        campaign_cli.Project,
        "discover",
        lambda: SimpleNamespace(root=root),
    )


def event(kind: str, *, step: int, run_id: str = "run-1"):
    return SimpleNamespace(
        kind=kind,
        step=step,
        campaign_id="campaign-1",
        stage="ready" if step else None,
        action="queued" if step else None,
        request_id="request-1" if step else None,
        detail=None,
        run_id=run_id,
    )


def seed_history(root) -> None:
    store = JsonOrchestrationEventStore(
        root / ".creativeos" / "runtime" / "orchestration-events"
    )
    store.append(
        campaign_id="campaign-1",
        run_id="run-1",
        policy="once",
        events=(event("campaign-started", step=0), event("step-completed", step=1)),
    )
    store.append(
        campaign_id="campaign-1",
        run_id="run-2",
        policy="until-complete",
        events=(event("campaign-finished", step=2, run_id="run-2"),),
    )


def test_history_renders_all_runs_in_persisted_order(monkeypatch, tmp_path) -> None:
    install_project(monkeypatch, tmp_path)
    seed_history(tmp_path)

    result = runner.invoke(app, ["campaign", "history", "campaign-1"], terminal_width=220)
    output = " ".join(result.stdout.split())

    assert result.exit_code == 0
    assert "Campaign Orchestration History: campaign-1" in output
    assert output.index("run-1") < output.index("run-2")
    assert "campaign-started" in output
    assert "campaign-finished" in output


def test_history_can_filter_by_run_id(monkeypatch, tmp_path) -> None:
    install_project(monkeypatch, tmp_path)
    seed_history(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "history", "campaign-1", "--run-id", "run-2"],
        terminal_width=220,
    )

    assert result.exit_code == 0
    assert "run-2" in result.stdout
    assert "run-1" not in result.stdout


def test_history_reports_missing_history_without_error(monkeypatch, tmp_path) -> None:
    install_project(monkeypatch, tmp_path)

    result = runner.invoke(app, ["campaign", "history", "missing"])

    assert result.exit_code == 0
    assert "No orchestration history found for missing." in result.stdout


def test_history_reports_corrupt_store_and_exits_one(monkeypatch, tmp_path) -> None:
    install_project(monkeypatch, tmp_path)
    directory = tmp_path / ".creativeos" / "runtime" / "orchestration-events"
    directory.mkdir(parents=True)
    (directory / "campaign-1.json").write_text("not-json", encoding="utf-8")

    result = runner.invoke(app, ["campaign", "history", "campaign-1"])

    assert result.exit_code == 1
    assert "history is corrupt" in result.stdout


def test_history_help_is_visible() -> None:
    result = runner.invoke(app, ["campaign", "history", "--help"])

    assert result.exit_code == 0
    assert "Display durable orchestration events" in result.stdout
    assert "Show only one persisted orchestration run" in result.stdout
