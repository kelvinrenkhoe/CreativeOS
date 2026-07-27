from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from services.campaign_orchestration import CampaignRun, WorkflowEvidence
from services.campaign_queue import ExecutionQueue, QueueJob
from services.operations_dashboard import (
    AuditEvent,
    AuditHistory,
    AuditHistoryService,
    OperationsDashboardService,
)
from services.provider_execution import ExecutionApproval, ExecutionRequest

NOW = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def run(
    campaign_id: str = "no-lose-guard-launch",
    stage: str = "planned",
) -> CampaignRun:
    evidence = ()
    if stage == "ready":
        evidence = (
            WorkflowEvidence(
                kind="approved-assets",
                reference_id="approval-01",
                recorded_by="Kelvin",
            ),
        )
    return CampaignRun(
        campaign_id=campaign_id,
        work_id="no-lose-guard",
        stage=stage,
        plan=None,
        cinematic_treatment=None,
        video_prompt=None,
        image_plan=None,
        evidence=evidence,
    )


def job(request_id: str, status: str, reason: str | None = None) -> QueueJob:
    request = ExecutionRequest(
        request_id=request_id,
        asset_id=f"asset-{request_id}",
        work_id="no-lose-guard",
        media_type="video",
        provider="open-video",
        prompt="Cinematic performance.",
    )
    approval = ExecutionApproval(
        asset_id=request.asset_id,
        media_type="video",
        provider="open-video",
        approved_by="Kelvin",
    )
    return QueueJob(
        request=request,
        approval=approval,
        scheduled_for=NOW,
        priority=5,
        status=status,
        failure_reason=reason,
    )


def event(
    event_id: str,
    *,
    occurred_at: datetime = NOW,
    category: str = "campaign",
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        category=category,
        action="advanced",
        subject_id="no-lose-guard-launch",
        actor="Kelvin",
        reference_id="evidence-01",
    )


def test_records_normalized_attributable_audit_event() -> None:
    history = AuditHistoryService().record(
        AuditHistory(),
        replace(event("event-01"), category=" Campaign ", action=" Advanced "),
    )

    assert history.events[0].category == "campaign"
    assert history.events[0].action == "advanced"
    assert history.events[0].actor == "Kelvin"


def test_rejects_duplicate_event_identity() -> None:
    service = AuditHistoryService()
    history = service.record(AuditHistory(), event("event-01"))

    with pytest.raises(ValueError, match="already recorded"):
        service.record(history, event("event-01"))


def test_rejects_unknown_category_and_naive_timestamp() -> None:
    service = AuditHistoryService()

    with pytest.raises(ValueError, match="unsupported audit category"):
        service.record(AuditHistory(), event("event-01", category="unknown"))

    with pytest.raises(ValueError, match="timezone"):
        service.record(
            AuditHistory(),
            event("event-02", occurred_at=datetime(2026, 9, 1, 9, 0)),
        )


def test_builds_deterministic_operations_snapshot() -> None:
    history = AuditHistory(
        events=(
            event("older", occurred_at=NOW),
            event("newer", occurred_at=NOW + timedelta(minutes=5), category="queue"),
        )
    )
    queue = ExecutionQueue(
        jobs=(
            job("scheduled-01", "scheduled"),
            job("failed-01", "failed", "provider unavailable"),
            job("completed-01", "completed"),
        )
    )

    dashboard = OperationsDashboardService().build(
        (run("second"), run("first", "ready")),
        queue,
        history,
        recent_event_limit=1,
    )

    assert [item.campaign_id for item in dashboard.campaigns] == ["first", "second"]
    assert dashboard.campaigns[0].requires_action == "Record publication-receipt evidence"
    assert dashboard.queue_status_counts == (
        ("completed", 1),
        ("failed", 1),
        ("scheduled", 1),
    )
    assert dashboard.failed_jobs[0].request_id == "failed-01"
    assert dashboard.failed_jobs[0].reason == "provider unavailable"
    assert [item.event_id for item in dashboard.recent_events] == ["newer"]


def test_snapshot_does_not_mutate_source_state() -> None:
    campaign = run()
    queue = ExecutionQueue(jobs=(job("scheduled-01", "scheduled"),))
    history = AuditHistory(events=(event("event-01"),))

    OperationsDashboardService().build((campaign,), queue, history)

    assert campaign.stage == "planned"
    assert queue.jobs[0].status == "scheduled"
    assert history.events[0].event_id == "event-01"


def test_rejects_inconsistent_operational_state() -> None:
    service = OperationsDashboardService()

    with pytest.raises(ValueError, match="campaign IDs must be unique"):
        service.build((run(), run()), ExecutionQueue(), AuditHistory())

    with pytest.raises(ValueError, match="failure reason"):
        service.build(
            (),
            ExecutionQueue(jobs=(job("failed-01", "failed"),)),
            AuditHistory(),
        )


def test_rejects_negative_recent_event_limit() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        OperationsDashboardService().build(
            (),
            ExecutionQueue(),
            AuditHistory(),
            recent_event_limit=-1,
        )
