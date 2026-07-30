"""Tests for evidence-based, human-reviewed campaign adaptation."""

from dataclasses import replace

import pytest

from services.campaign_measurement import CampaignMeasurement, CampaignMetricSummary
from services.evidence_based_adaptation import EvidenceBasedAdaptationService
from services.recommendation_feedback import RecommendationDecision

CAMPAIGN_ID = "no-lose-guard-launch"


def measurement(value: float) -> CampaignMeasurement:
    """Create a campaign measurement with one Instagram reach metric."""
    return CampaignMeasurement(
        campaign_id=CAMPAIGN_ID,
        asset_ids=("video-01",),
        metrics=(
            CampaignMetricSummary(
                platform="instagram",
                metric="reach",
                value=value,
                asset_count=1,
                publication_count=1,
                latest_observed_at="2026-07-30T10:00:00Z",
            ),
        ),
    )


def test_propose_preserves_evidence_and_creates_reviewable_recommendation() -> None:
    service = EvidenceBasedAdaptationService()
    baseline = measurement(1000)
    current = measurement(500)

    proposal = service.propose(current, baseline)

    assert proposal.campaign_id == CAMPAIGN_ID
    assert proposal.baseline is baseline
    assert proposal.current is current
    assert proposal.assessment.campaign_id == CAMPAIGN_ID
    assert proposal.requires_review is True

    assert len(proposal.assessment.signals) == 1
    signal = proposal.assessment.signals[0]
    assert signal.kind == "performance-decline"
    assert signal.severity == "high"
    assert signal.score == 0.5
    assert signal.platform == "instagram"
    assert signal.metric == "reach"

    assert len(proposal.recommendations.recommendations) == 1
    recommendation = proposal.recommendations.recommendations[0]
    assert recommendation.id == "recommendation-001"
    assert recommendation.kind == "review-platform-strategy"
    assert recommendation.priority == "high"
    assert recommendation.signal_kind == signal.kind


def test_propose_without_fatigue_requires_no_review() -> None:
    proposal = EvidenceBasedAdaptationService().propose(
        measurement(1100),
        measurement(1000),
    )

    assert proposal.assessment.signals == ()
    assert proposal.recommendations.recommendations == ()
    assert proposal.requires_review is False


def test_review_records_named_decision_without_changing_proposal() -> None:
    service = EvidenceBasedAdaptationService()
    proposal = service.propose(measurement(500), measurement(1000))
    recommendation = proposal.recommendations.recommendations[0]

    reviewed = service.review(
        proposal,
        (
            RecommendationDecision(
                recommendation_id=recommendation.id,
                decision="accept",
                decided_by="Kelvin Rankie",
                reason="Refresh the Instagram approach for the next campaign window",
            ),
        ),
    )

    assert reviewed.proposal is proposal
    assert reviewed.outcome.campaign_id == CAMPAIGN_ID
    assert reviewed.outcome.accepted == (recommendation,)
    assert reviewed.outcome.rejected == ()
    assert reviewed.outcome.pending == ()
    assert reviewed.has_pending_decisions is False

    assert reviewed.proposal.current == measurement(500)
    assert reviewed.proposal.baseline == measurement(1000)


def test_review_leaves_undecided_recommendations_pending() -> None:
    service = EvidenceBasedAdaptationService()
    proposal = service.propose(measurement(500), measurement(1000))

    reviewed = service.review(proposal, ())

    assert reviewed.outcome.accepted == ()
    assert reviewed.outcome.rejected == ()
    assert reviewed.outcome.pending == proposal.recommendations.recommendations
    assert reviewed.has_pending_decisions is True


def test_review_rejects_mismatched_proposal_campaign() -> None:
    service = EvidenceBasedAdaptationService()
    proposal = service.propose(measurement(500), measurement(1000))
    invalid = replace(proposal, campaign_id="another-campaign")

    with pytest.raises(
        ValueError,
        match="proposal campaign_id does not match current measurement",
    ):
        service.review(invalid, ())
