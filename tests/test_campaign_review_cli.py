"""CLI tests for durable campaign human review decisions."""

from datetime import UTC, datetime
from types import SimpleNamespace

from typer.testing import CliRunner

from cli.campaign import app
from services.review_decision_store import JsonReviewDecisionStore
from services.runtime_checkpoints import RuntimeCheckpoint

runner = CliRunner()
REVIEW_ID = "review:no-lose-guard-launch:uncertain-action:runtime-123"


def configured_run():
    return SimpleNamespace(
        campaign_id="no-lose-guard-launch",
        work_id="no-lose-guard",
    )


def uncertain_checkpoint():
    return RuntimeCheckpoint(
        checkpoint_id="runtime-123",
        campaign_id="no-lose-guard-launch",
        action_key="execution:request-9",
        status="uncertain",
        started_at=datetime(2026, 7, 31, 8, tzinfo=UTC),
    )


def configure_review(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonCampaignRunStore.load",
        lambda _store, _campaign_id: configured_run(),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonRuntimeCheckpointStore.load",
        lambda _store: (uncertain_checkpoint(),),
    )


def test_review_lists_only_campaign_pending_items(tmp_path, monkeypatch) -> None:
    configure_review(monkeypatch, tmp_path)

    result = runner.invoke(app, ["review", "no-lose-guard-launch"])

    assert result.exit_code == 0
    assert "Campaign Human Reviews" in result.stdout
    assert "review:no-lose" in result.stdout
    assert "uncertain-action" in result.stdout
    assert "confirm-completed" in result.stdout
    assert "confirm-not-completed" in result.stdout


def test_review_records_one_attributable_decision_and_audit_event(
    tmp_path,
    monkeypatch,
) -> None:
    configure_review(monkeypatch, tmp_path)

    result = runner.invoke(
        app,
        [
            "review",
            "no-lose-guard-launch",
            "--review-id",
            REVIEW_ID,
            "--decision",
            "confirm-not-completed",
            "--decided-by",
            "Kelvin",
            "--reason",
            "Provider has no matching output",
        ],
    )

    assert result.exit_code == 0
    assert "Recorded confirm-not-completed" in result.stdout
    assert "No pending reviews." in result.stdout
    decisions = JsonReviewDecisionStore(
        tmp_path / ".creativeos/runtime/review-decisions.json"
    ).load()
    assert len(decisions) == 1
    assert decisions[0].decided_by == "Kelvin"
    assert decisions[0].reason == "Provider has no matching output"

    history_path = tmp_path / ".creativeos/runtime/audit-history.json"
    assert history_path.exists()
    assert "review-decision:" in history_path.read_text(encoding="utf-8")


def test_review_rejects_negative_decision_without_reason(
    tmp_path,
    monkeypatch,
) -> None:
    configure_review(monkeypatch, tmp_path)

    result = runner.invoke(
        app,
        [
            "review",
            "no-lose-guard-launch",
            "--review-id",
            REVIEW_ID,
            "--decision",
            "confirm-not-completed",
            "--decided-by",
            "Kelvin",
        ],
    )

    assert result.exit_code == 1
    assert "requires a reason" in result.stdout
    assert not (tmp_path / ".creativeos/runtime/review-decisions.json").exists()


def test_review_identical_replay_is_idempotent_and_does_not_duplicate_audit(
    tmp_path,
    monkeypatch,
) -> None:
    configure_review(monkeypatch, tmp_path)
    arguments = [
        "review",
        "no-lose-guard-launch",
        "--review-id",
        REVIEW_ID,
        "--decision",
        "confirm-completed",
        "--decided-by",
        "Kelvin",
    ]

    first = runner.invoke(app, arguments)
    second = runner.invoke(app, arguments)

    assert first.exit_code == 0
    assert second.exit_code == 0
    decisions = JsonReviewDecisionStore(
        tmp_path / ".creativeos/runtime/review-decisions.json"
    ).load()
    assert len(decisions) == 1
    history_path = tmp_path / ".creativeos/runtime/audit-history.json"
    assert history_path.read_text(encoding="utf-8").count('"event_id": "review-decision:') == 1


def test_review_requires_complete_explicit_decision_input(
    tmp_path,
    monkeypatch,
) -> None:
    configure_review(monkeypatch, tmp_path)

    result = runner.invoke(
        app,
        ["review", "no-lose-guard-launch", "--decision", "confirm-completed"],
    )

    assert result.exit_code == 1
    assert "must be supplied together" in result.stdout


def test_review_never_invokes_provider_execution(tmp_path, monkeypatch) -> None:
    configure_review(monkeypatch, tmp_path)

    def provider_call(*_args, **_kwargs):
        raise AssertionError("review must not invoke provider execution")

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        provider_call,
    )

    result = runner.invoke(app, ["review", "no-lose-guard-launch"])

    assert result.exit_code == 0
