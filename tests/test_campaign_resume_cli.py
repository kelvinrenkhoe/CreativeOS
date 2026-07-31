"""Tests for safe campaign checkpoint reconciliation and resume CLI."""

from datetime import UTC, datetime
from types import SimpleNamespace

from typer.testing import CliRunner

from cli.campaign import app
from services.operations_dashboard import AuditEvent, AuditHistory
from services.persistent_queue import PersistentQueue
from services.review_decision_store import StoredReviewDecision
from services.runtime_checkpoints import JsonRuntimeCheckpointStore, RuntimeCheckpoint

runner = CliRunner()
NOW = datetime(2026, 7, 31, 9, tzinfo=UTC)
CAMPAIGN_ID = "no-lose-guard-launch"
CHECKPOINT_ID = "runtime-123"
REVIEW_ID = f"review:{CAMPAIGN_ID}:uncertain-action:{CHECKPOINT_ID}"


def checkpoint(*, status: str = "uncertain") -> RuntimeCheckpoint:
    return RuntimeCheckpoint(
        checkpoint_id=CHECKPOINT_ID,
        campaign_id=CAMPAIGN_ID,
        action_key="execution:request-9",
        status=status,
        started_at=datetime(2026, 7, 31, 8, tzinfo=UTC),
    )


def decision(value: str = "confirm-not-completed") -> StoredReviewDecision:
    return StoredReviewDecision(
        review_id=REVIEW_ID,
        campaign_id=CAMPAIGN_ID,
        kind="uncertain-action",
        subject_id=CHECKPOINT_ID,
        decision=value,
        decided_by="Kelvin",
        decided_at=NOW,
        reason="Verified with the provider",
    )


def configure_resume(monkeypatch, tmp_path, *, stored_decision=None, events=()):
    current = checkpoint()
    observed = {"reconcile_calls": 0, "history_saves": 0}
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonCampaignRunStore.load",
        lambda _store, _campaign_id: SimpleNamespace(
            campaign_id=CAMPAIGN_ID,
            work_id="no-lose-guard",
            stage="in-production",
        ),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonRuntimeCheckpointStore.load",
        lambda _store: (current,),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonReviewDecisionStore.load",
        lambda _store: () if stored_decision is None else (stored_decision,),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonExecutionQueueStore.load",
        lambda _store: PersistentQueue(),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonAuditHistoryStore.load",
        lambda _store: AuditHistory(events=events),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonAuditHistoryStore.save",
        lambda _store, _history: observed.__setitem__(
            "history_saves", observed["history_saves"] + 1
        ),
    )

    def reconcile(_store, supplied, **kwargs):
        observed["reconcile_calls"] += 1
        observed["checkpoint"] = supplied
        observed["decision"] = kwargs["decision"]
        return SimpleNamespace(result_action="confirmed-not-completed")

    monkeypatch.setattr(
        "cli.campaign.JsonRuntimeCheckpointStore.reconcile",
        reconcile,
    )
    return observed


def test_checkpoint_confirm_not_completed_becomes_retryable(tmp_path) -> None:
    store = JsonRuntimeCheckpointStore(tmp_path / "checkpoints.json")
    started, acquired = store.begin(
        campaign_id=CAMPAIGN_ID,
        action_key="execution:request-9",
        now=NOW,
    )
    assert acquired is True
    uncertain = store.mark_uncertain(started, now=NOW)

    retryable = store.reconcile(
        uncertain,
        decision="confirm-not-completed",
        now=NOW,
    )
    restarted, reacquired = store.begin(
        campaign_id=CAMPAIGN_ID,
        action_key="execution:request-9",
        now=NOW,
    )

    assert retryable.status == "retryable"
    assert reacquired is True
    assert restarted.status == "started"


def test_resume_reconciles_one_not_completed_decision(tmp_path, monkeypatch) -> None:
    observed = configure_resume(
        monkeypatch,
        tmp_path,
        stored_decision=decision(),
    )

    result = runner.invoke(app, ["resume", CAMPAIGN_ID])

    assert result.exit_code == 0
    assert observed["reconcile_calls"] == 1
    assert observed["decision"] == "confirm-not-completed"
    assert observed["history_saves"] == 1
    assert "Campaign Runtime Resume" in result.stdout
    assert "Replayed" in result.stdout
    assert "No" in result.stdout


def test_resume_replays_existing_reconciliation_without_mutation(
    tmp_path,
    monkeypatch,
) -> None:
    event = AuditEvent(
        event_id=f"checkpoint-reconciliation:{REVIEW_ID}",
        occurred_at=NOW,
        category="execution",
        action="confirm-not-completed",
        subject_id=CHECKPOINT_ID,
        actor="Kelvin",
        reference_id=REVIEW_ID,
    )
    observed = configure_resume(
        monkeypatch,
        tmp_path,
        stored_decision=decision(),
        events=(event,),
    )

    result = runner.invoke(app, ["resume", CAMPAIGN_ID])

    assert result.exit_code == 0
    assert observed["reconcile_calls"] == 0
    assert observed["history_saves"] == 0
    assert "Yes" in result.stdout


def test_resume_rejects_missing_matching_decision(tmp_path, monkeypatch) -> None:
    observed = configure_resume(monkeypatch, tmp_path)

    result = runner.invoke(app, ["resume", CAMPAIGN_ID])

    assert result.exit_code == 1
    assert observed["reconcile_calls"] == 0
    assert "no recorded uncertain-action decision" in result.stdout


def test_resume_requires_completed_receipt_for_confirm_completed(
    tmp_path,
    monkeypatch,
) -> None:
    observed = configure_resume(
        monkeypatch,
        tmp_path,
        stored_decision=decision("confirm-completed"),
    )

    result = runner.invoke(app, ["resume", CAMPAIGN_ID])

    assert result.exit_code == 1
    assert observed["reconcile_calls"] == 0
    assert "matching completed queue receipt" in result.stdout


def test_resume_never_invokes_provider_execution(tmp_path, monkeypatch) -> None:
    configure_resume(
        monkeypatch,
        tmp_path,
        stored_decision=decision(),
    )

    def provider_call(*_args, **_kwargs):
        raise AssertionError("resume must not invoke provider execution")

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        provider_call,
    )

    result = runner.invoke(app, ["resume", CAMPAIGN_ID])

    assert result.exit_code == 0
