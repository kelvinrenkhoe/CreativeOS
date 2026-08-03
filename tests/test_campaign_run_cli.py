"""CLI tests for one-action campaign runtime execution."""

from types import SimpleNamespace

from typer.testing import CliRunner

from cli.campaign import app
from services.campaign_queue import ExecutionQueue
from services.operations_dashboard import AuditHistory
from services.persistent_queue import PersistentQueue, QueueStateError

runner = CliRunner()


def runtime_run(*, stage: str):
    return SimpleNamespace(
        campaign_id="no-lose-guard-launch",
        work_id="no-lose-guard",
        stage=stage,
        plan=SimpleNamespace(work_name="No Lose Guard"),
    )


def configure_runtime(monkeypatch, tmp_path, *, stage: str):
    queue = ExecutionQueue()
    history = AuditHistory()
    observed = {"advance_calls": 0}

    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonCampaignRunStore.load",
        lambda _store, _campaign_id: runtime_run(stage=stage),
    )
    monkeypatch.setattr(
        "cli.campaign._validate_campaign_preflight",
        lambda _project, _campaign_name: None,
    )
    monkeypatch.setattr(
        "cli.campaign.JsonExecutionQueueStore.load",
        lambda _store: PersistentQueue(queue=queue),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonAuditHistoryStore.load",
        lambda _store: history,
    )
    return queue, history, observed


def test_run_advances_exactly_one_safe_action(tmp_path, monkeypatch) -> None:
    queue, history, observed = configure_runtime(
        monkeypatch,
        tmp_path,
        stage="planned",
    )

    def advance(
        _runtime,
        campaign_id,
        run_store,
        checkpoint_store,
        supplied_queue,
        supplied_history,
        adapters,
        *,
        worker_id,
        now,
    ):
        observed["advance_calls"] += 1
        observed["campaign_id"] = campaign_id
        observed["queue"] = supplied_queue
        observed["history"] = supplied_history
        observed["adapters"] = adapters
        observed["worker_id"] = worker_id
        return SimpleNamespace(
            uncertain=False,
            checkpoint=None,
            result=SimpleNamespace(
                run=runtime_run(stage="in-production"),
                queue=supplied_queue,
                history=supplied_history,
                action="production-started",
                request_id=None,
                paused=False,
            ),
        )

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        advance,
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 0
    assert observed["advance_calls"] == 1
    assert observed["campaign_id"] == "no-lose-guard-launch"
    assert observed["queue"] == queue
    assert observed["history"] == history
    assert observed["adapters"] == ()
    assert observed["worker_id"] == "creativeos-cli"
    assert "Campaign Runtime Action" in result.stdout
    assert "in-production" in result.stdout
    assert "production-started" in result.stdout
    assert "Paused" in result.stdout
    assert "No" in result.stdout


def test_run_reports_human_review_pause_without_accepting_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    queue, history, _observed = configure_runtime(
        monkeypatch,
        tmp_path,
        stage="ready",
    )

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        lambda *_args, **_kwargs: SimpleNamespace(
            uncertain=False,
            checkpoint=None,
            result=SimpleNamespace(
                run=runtime_run(stage="ready"),
                queue=queue,
                history=history,
                action="awaiting-publication",
                request_id=None,
                paused=True,
            ),
        ),
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 0
    assert "ready" in result.stdout
    assert "awaiting-publication" in result.stdout
    assert "Yes" in result.stdout


def test_run_returns_non_zero_for_invalid_durable_state(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonCampaignRunStore.load",
        lambda _store, _campaign_id: runtime_run(stage="planned"),
    )
    monkeypatch.setattr(
        "cli.campaign._validate_campaign_preflight",
        lambda _project, _campaign_name: None,
    )

    def fail(_store):
        raise QueueStateError("invalid queue snapshot")

    monkeypatch.setattr("cli.campaign.JsonExecutionQueueStore.load", fail)

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "invalid queue snapshot" in result.stdout


def test_run_refuses_due_provider_work_without_explicit_configuration(
    tmp_path,
    monkeypatch,
) -> None:
    configure_runtime(monkeypatch, tmp_path, stage="in-production")
    due_job = SimpleNamespace(request=SimpleNamespace(work_id="no-lose-guard"))
    monkeypatch.setattr(
        "cli.campaign.CampaignQueueService.ready",
        lambda _service, _queue, *, now: (due_job,),
    )

    def must_not_advance(*_args, **_kwargs):
        raise AssertionError("runtime must not execute unconfigured provider work")

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        must_not_advance,
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 1
    assert "explicit CLI provider configuration" in result.stdout


def test_run_blocks_before_runtime_state_when_preflight_fails(
    tmp_path,
    monkeypatch,
) -> None:
    observed = {
        "queue_loads": 0,
        "advance_calls": 0,
    }

    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonCampaignRunStore.load",
        lambda _store, _campaign_id: runtime_run(stage="planned"),
    )

    def fail_preflight(_project, campaign_name):
        assert campaign_name == "No Lose Guard"
        raise ValueError(
            'campaign readiness preflight failed for "No Lose Guard": '
            'Release date. Run: creativeos doctor --campaign "No Lose Guard"'
        )

    monkeypatch.setattr(
        "cli.campaign._validate_campaign_preflight",
        fail_preflight,
    )

    def must_not_load_queue(_store):
        observed["queue_loads"] += 1
        raise AssertionError("queue state must not be loaded")

    monkeypatch.setattr(
        "cli.campaign.JsonExecutionQueueStore.load",
        must_not_load_queue,
    )

    def must_not_advance(*_args, **_kwargs):
        observed["advance_calls"] += 1
        raise AssertionError("runtime must not advance")

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        must_not_advance,
    )

    result = runner.invoke(app, ["run", "no-lose-guard-launch"])

    assert result.exit_code == 1
    assert observed["queue_loads"] == 0
    assert observed["advance_calls"] == 0
    assert "campaign readiness preflight failed" in result.stdout
    assert 'creativeos doctor --campaign "No Lose Guard"' in result.stdout
