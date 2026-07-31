"""CLI tests for the read-only campaign operations dashboard."""

from datetime import UTC, datetime
from types import SimpleNamespace

from rich.console import Console
from typer.testing import CliRunner

from cli.campaign import (
    ANALYTICS_REFRESH_PATH,
    AUDIT_HISTORY_PATH,
    CHECKPOINTS_PATH,
    QUEUE_PATH,
    REVIEW_DECISIONS_PATH,
    app,
)
from services.campaign_run_state import CampaignRunCorruptedError, JsonCampaignRunStore
from services.human_review_inbox import ReviewInbox, ReviewItem
from services.operations_dashboard import AuditHistory
from services.persistent_queue import PersistentQueue

runner = CliRunner()
NOW = datetime(2026, 8, 1, 9, tzinfo=UTC)


def run(campaign_id):
    return SimpleNamespace(
        campaign_id=campaign_id,
        work_id=campaign_id.removesuffix("-launch"),
        stage="in-production",
        requires_action="Record approved-assets evidence",
        evidence=(),
    )


def review(campaign_id, checkpoint_id):
    return ReviewItem(
        review_id=f"review:{campaign_id}:uncertain-action:{checkpoint_id}",
        campaign_id=campaign_id,
        kind="uncertain-action",
        subject_id=checkpoint_id,
        title="Reconcile uncertain runtime action",
        detail="Confirm whether provider work completed.",
        priority="urgent",
        allowed_decisions=("confirm-completed", "confirm-not-completed"),
    )


def test_dashboard_shows_multiple_campaigns_and_safe_recommendations(
    tmp_path,
    monkeypatch,
) -> None:
    campaign_runs = (
        run("another-launch"),
        run("no-lose-guard-launch"),
    )
    checkpoints = (
        SimpleNamespace(
            campaign_id="another-launch",
            checkpoint_id="checkpoint-a",
            status="uncertain",
        ),
        SimpleNamespace(
            campaign_id="no-lose-guard-launch",
            checkpoint_id="checkpoint-n",
            status="uncertain",
        ),
    )
    reviews = ReviewInbox(
        items=(
            review("another-launch", "checkpoint-a"),
            review("no-lose-guard-launch", "checkpoint-n"),
        )
    )
    decisions = (
        SimpleNamespace(
            review_id=reviews.items[1].review_id,
            campaign_id="no-lose-guard-launch",
            kind="uncertain-action",
            subject_id="checkpoint-n",
        ),
    )

    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(JsonCampaignRunStore, "load_all", lambda _store: campaign_runs)
    monkeypatch.setattr(
        "cli.campaign.HumanReviewInboxService.build",
        lambda _service, _runs, **_kwargs: reviews,
    )
    monkeypatch.setattr("cli.campaign.console", Console(width=240))

    optional_paths = (
        QUEUE_PATH,
        AUDIT_HISTORY_PATH,
        CHECKPOINTS_PATH,
        REVIEW_DECISIONS_PATH,
        ANALYTICS_REFRESH_PATH,
    )
    for path in optional_paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        "cli.campaign.JsonExecutionQueueStore.load",
        lambda _store: PersistentQueue(),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonAuditHistoryStore.load",
        lambda _store: AuditHistory(),
    )
    monkeypatch.setattr(
        "cli.campaign.JsonRuntimeCheckpointStore.load",
        lambda _store: checkpoints,
    )
    monkeypatch.setattr(
        "cli.campaign.JsonReviewDecisionStore.load",
        lambda _store: decisions,
    )
    monkeypatch.setattr(
        "cli.campaign.JsonAnalyticsRefreshStore.load",
        lambda _store: (),
    )

    before = {
        path: (tmp_path / path).read_text(encoding="utf-8")
        for path in optional_paths
    }

    def provider_call(*_args, **_kwargs):
        raise AssertionError("dashboard must not execute providers or advance runtime")

    monkeypatch.setattr(
        "cli.campaign.CheckpointedCampaignRuntime.advance",
        provider_call,
    )

    result = runner.invoke(app, ["dashboard"])

    after = {
        path: (tmp_path / path).read_text(encoding="utf-8")
        for path in optional_paths
    }
    assert result.exit_code == 0
    assert before == after
    assert result.stdout.index("another-launch") < result.stdout.index(
        "no-lose-guard-launch"
    )
    assert "creativeos campaign review another-launch" in result.stdout
    assert "creativeos campaign resume no-lose-guard-launch" in result.stdout
    assert "Analytics refresh is not configured." in result.stdout


def test_dashboard_treats_absent_optional_state_as_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(JsonCampaignRunStore, "load_all", lambda _store: ())
    monkeypatch.setattr(
        "cli.campaign.HumanReviewInboxService.build",
        lambda _service, _runs, **_kwargs: ReviewInbox(items=()),
    )

    result = runner.invoke(app, ["dashboard"])

    assert result.exit_code == 0
    assert "No persisted campaign runs." in result.stdout
    assert "Queue is empty." in result.stdout
    assert "Analytics refresh is not configured." in result.stdout
    assert "No audit activity recorded." in result.stdout


def test_dashboard_fails_closed_for_invalid_campaign_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )

    def fail(_store):
        raise CampaignRunCorruptedError("Campaign run store is corrupt")

    monkeypatch.setattr(JsonCampaignRunStore, "load_all", fail)

    result = runner.invoke(app, ["dashboard"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "corrupt" in result.stdout
