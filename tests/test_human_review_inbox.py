from dataclasses import replace
from datetime import UTC, datetime

import pytest

from services.campaign_orchestration import CampaignOrchestrationService
from services.human_review_inbox import (
    HumanReviewInboxService,
    PendingPublication,
    ReviewDecision,
)
from services.provider_execution import ExecutionRequest
from services.publishing import PublicationRequest
from services.recommendation_feedback import RecommendationSet, StrategyRecommendation
from services.runtime_checkpoints import RuntimeCheckpoint
from tests.test_campaign_orchestration import campaign, context


def run(campaign_id: str = "campaign-1", work_id: str = "no-way-back"):
    plan = replace(campaign(), work_id=work_id)
    return CampaignOrchestrationService().prepare(
        campaign_id,
        context(),
        plan,
    )


def execution(work_id: str = "no-way-back") -> ExecutionRequest:
    return ExecutionRequest(
        request_id="request-1",
        asset_id="asset-1",
        work_id=work_id,
        media_type="video",
        provider="runway",
        prompt="A cinematic performance",
    )


def publication() -> PendingPublication:
    return PendingPublication(
        campaign_id="campaign-1",
        request=PublicationRequest(
            asset_id="asset-2",
            platform="Instagram",
            content="New music soon",
        ),
    )


def uncertain() -> RuntimeCheckpoint:
    return RuntimeCheckpoint(
        checkpoint_id="runtime-123",
        campaign_id="campaign-1",
        action_key="execution:request-9",
        status="uncertain",
        started_at=datetime(2026, 7, 29, tzinfo=UTC),
    )


def recommendations() -> RecommendationSet:
    return RecommendationSet(
        campaign_id="campaign-1",
        recommendations=(
            StrategyRecommendation(
                id="recommendation-001",
                kind="refresh-visual-direction",
                priority="high",
                action="Refresh the visual direction",
                reason="Recent posts use the same visual pattern",
                signal_kind="visual-repetition",
                asset_id="asset-3",
            ),
        ),
    )


def test_builds_one_prioritized_inbox_from_existing_human_gates() -> None:
    inbox = HumanReviewInboxService().build(
        (run(),),
        (execution(),),
        (publication(),),
        (uncertain(),),
        (recommendations(),),
    )

    assert tuple(item.kind for item in inbox.items) == (
        "uncertain-action",
        "publication-approval",
        "strategy-recommendation",
        "asset-approval",
    )
    assert inbox.requires_review is True
    assert inbox.items[0].allowed_decisions == (
        "confirm-completed",
        "confirm-not-completed",
    )


def test_review_ids_are_stable_independent_of_input_order() -> None:
    service = HumanReviewInboxService()
    first = service.build((run(),), (execution(),), (publication(),))
    second = service.build((run(),), (execution(),), tuple(reversed((publication(),))))

    assert first == second
    assert first.items[-1].review_id == ("review:campaign-1:asset-approval:request-1")


def test_records_attributable_decisions_without_mutating_source_items() -> None:
    service = HumanReviewInboxService()
    inbox = service.build((run(),), (execution(),), (publication(),))

    outcome = service.review(
        inbox,
        (
            ReviewDecision(
                review_id=inbox.items[0].review_id,
                decision="APPROVE",
                decided_by="Kelvin",
            ),
        ),
    )

    assert len(outcome.decided) == 1
    assert outcome.decided[0][1].decision == "approve"
    assert outcome.pending == (inbox.items[1],)
    assert inbox.requires_review is True


def test_uncertain_action_cannot_be_approved_or_retried() -> None:
    service = HumanReviewInboxService()
    inbox = service.build((run(),), checkpoints=(uncertain(),))

    with pytest.raises(ValueError, match="confirm-completed"):
        service.review(
            inbox,
            (
                ReviewDecision(
                    review_id=inbox.items[0].review_id,
                    decision="retry",
                    decided_by="Kelvin",
                ),
            ),
        )


def test_negative_decision_requires_reason() -> None:
    service = HumanReviewInboxService()
    inbox = service.build((run(),), publications=(publication(),))

    with pytest.raises(ValueError, match="requires a reason"):
        service.review(
            inbox,
            (
                ReviewDecision(
                    review_id=inbox.items[0].review_id,
                    decision="reject",
                    decided_by="Kelvin",
                ),
            ),
        )


def test_rejects_sources_not_owned_by_a_known_campaign() -> None:
    service = HumanReviewInboxService()

    with pytest.raises(ValueError, match="unknown work_id"):
        service.build((run(),), execution_requests=(execution("other-song"),))
    with pytest.raises(ValueError, match="unknown campaign_id"):
        service.build(
            (run(),),
            publications=(replace(publication(), campaign_id="other-campaign"),),
        )


def test_completed_checkpoints_and_empty_sources_need_no_review() -> None:
    completed = replace(
        uncertain(),
        status="completed",
        completed_at=datetime(2026, 7, 29, 1, tzinfo=UTC),
        result_action="execution-completed",
        request_id="request-9",
        resulting_stage="in-production",
    )

    inbox = HumanReviewInboxService().build((run(),), checkpoints=(completed,))

    assert inbox.items == ()
    assert inbox.requires_review is False
