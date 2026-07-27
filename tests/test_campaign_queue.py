from datetime import UTC, datetime, timedelta

import pytest

from services.campaign_queue import CampaignQueueService, ExecutionQueue
from services.provider_execution import (
    ExecutionApproval,
    ExecutionReceipt,
    ExecutionRequest,
)

NOW = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def request(request_id: str = "video-01") -> ExecutionRequest:
    return ExecutionRequest(
        request_id=request_id,
        asset_id="no-lose-guard-video-01",
        work_id="no-lose-guard",
        media_type=" Video ",
        provider=" Open-Video ",
        prompt=" A cinematic performance scene. ",
    )


def approval(provider: str = "open-video") -> ExecutionApproval:
    return ExecutionApproval(
        asset_id="no-lose-guard-video-01",
        media_type="video",
        provider=provider,
        approved_by="Kelvin",
    )


def receipt(request_id: str = "video-01") -> ExecutionReceipt:
    return ExecutionReceipt(
        request_id=request_id,
        asset_id="no-lose-guard-video-01",
        media_type="video",
        provider="open-video",
        external_id="generation-123",
    )


def scheduled_queue() -> ExecutionQueue:
    return CampaignQueueService().schedule(
        ExecutionQueue(),
        request(),
        approval(),
        scheduled_for=NOW,
        priority=5,
    )


def test_schedules_only_matching_approved_work() -> None:
    queue = scheduled_queue()

    assert len(queue.jobs) == 1
    assert queue.jobs[0].request.provider == "open-video"
    assert queue.jobs[0].approval.approved_by == "Kelvin"
    assert queue.jobs[0].status == "scheduled"


def test_rejects_duplicate_request_identity() -> None:
    service = CampaignQueueService()
    queue = scheduled_queue()

    with pytest.raises(ValueError, match="already queued"):
        service.schedule(
            queue,
            request(),
            approval(),
            scheduled_for=NOW + timedelta(hours=1),
        )


def test_rejects_mismatched_approval() -> None:
    with pytest.raises(PermissionError, match="does not match"):
        CampaignQueueService().schedule(
            ExecutionQueue(),
            request(),
            approval(provider="another-provider"),
            scheduled_for=NOW,
        )


def test_rejects_naive_schedule_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone"):
        CampaignQueueService().schedule(
            ExecutionQueue(),
            request(),
            approval(),
            scheduled_for=datetime(2026, 9, 1, 9, 0),
        )


def test_orders_ready_work_by_priority_schedule_and_identity() -> None:
    service = CampaignQueueService()
    queue = ExecutionQueue()
    for request_id, scheduled_for, priority in (
        ("later", NOW + timedelta(hours=1), 10),
        ("second", NOW, 5),
        ("first", NOW, 5),
        ("low", NOW - timedelta(minutes=5), 1),
    ):
        queue = service.schedule(
            queue,
            request(request_id),
            approval(),
            scheduled_for=scheduled_for,
            priority=priority,
        )

    ready = service.ready(queue, now=NOW)

    assert [job.request.request_id for job in ready] == ["first", "second", "low"]


def test_claims_due_work_without_executing_it() -> None:
    service = CampaignQueueService()

    queue = service.claim(scheduled_queue(), "video-01", worker_id="worker-1", now=NOW)

    assert queue.jobs[0].status == "claimed"
    assert queue.jobs[0].claimed_by == "worker-1"
    assert queue.jobs[0].receipt is None
    assert service.ready(queue, now=NOW) == ()


def test_rejects_claim_before_schedule() -> None:
    service = CampaignQueueService()
    queue = service.schedule(
        ExecutionQueue(),
        request(),
        approval(),
        scheduled_for=NOW + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="not ready"):
        service.claim(queue, "video-01", worker_id="worker-1", now=NOW)


def test_completes_claimed_work_with_matching_receipt() -> None:
    service = CampaignQueueService()
    claimed = service.claim(
        scheduled_queue(),
        "video-01",
        worker_id="worker-1",
        now=NOW,
    )

    completed = service.complete(claimed, "video-01", receipt())

    assert completed.jobs[0].status == "completed"
    assert completed.jobs[0].receipt == receipt()


def test_rejects_receipt_for_different_request() -> None:
    service = CampaignQueueService()
    claimed = service.claim(
        scheduled_queue(),
        "video-01",
        worker_id="worker-1",
        now=NOW,
    )

    with pytest.raises(ValueError, match="does not match"):
        service.complete(claimed, "video-01", receipt("another-request"))


def test_records_failure_and_cancels_only_unclaimed_work() -> None:
    service = CampaignQueueService()
    claimed = service.claim(
        scheduled_queue(),
        "video-01",
        worker_id="worker-1",
        now=NOW,
    )

    failed = service.fail(claimed, "video-01", reason="provider unavailable")

    assert failed.jobs[0].status == "failed"
    assert failed.jobs[0].failure_reason == "provider unavailable"

    with pytest.raises(ValueError, match="cancelled"):
        service.cancel(claimed, "video-01")

    cancelled = service.cancel(scheduled_queue(), "video-01")
    assert cancelled.jobs[0].status == "cancelled"
