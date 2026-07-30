"""Coordinate evidence-based, human-reviewed campaign adaptation."""

from collections.abc import Iterable
from dataclasses import dataclass

from services.campaign_measurement import CampaignMeasurement
from services.fatigue_signals import (
    CreativeFatigueInput,
    FatigueAssessment,
    FatigueSignalService,
)
from services.recommendation_feedback import (
    FeedbackOutcome,
    RecommendationDecision,
    RecommendationFeedbackService,
    RecommendationSet,
)


@dataclass(frozen=True, slots=True)
class AdaptationProposal:
    """Evidence and recommendations proposed for human review."""

    campaign_id: str
    baseline: CampaignMeasurement
    current: CampaignMeasurement
    assessment: FatigueAssessment
    recommendations: RecommendationSet

    @property
    def requires_review(self) -> bool:
        """Return whether the proposal contains recommendations."""
        return self.recommendations.requires_review


@dataclass(frozen=True, slots=True)
class AdaptationReview:
    """A review outcome that preserves the exact supporting proposal."""

    proposal: AdaptationProposal
    outcome: FeedbackOutcome

    @property
    def has_pending_decisions(self) -> bool:
        """Return whether any recommendations still need review."""
        return bool(self.outcome.pending)


class EvidenceBasedAdaptationService:
    """Propose and review adaptations without applying strategy changes."""

    def __init__(
        self,
        *,
        fatigue_service: FatigueSignalService | None = None,
        feedback_service: RecommendationFeedbackService | None = None,
    ) -> None:
        self.fatigue_service = fatigue_service or FatigueSignalService()
        self.feedback_service = feedback_service or RecommendationFeedbackService()

    def propose(
        self,
        current: CampaignMeasurement,
        baseline: CampaignMeasurement,
        *,
        creative: Iterable[CreativeFatigueInput] = (),
    ) -> AdaptationProposal:
        """Derive reviewable recommendations from preserved campaign evidence."""
        assessment = self.fatigue_service.assess(
            current,
            baseline,
            creative=tuple(creative),
        )
        recommendations = self.feedback_service.recommend(assessment)

        if recommendations.campaign_id != current.campaign_id:
            raise ValueError("recommendation campaign_id does not match current measurement")

        return AdaptationProposal(
            campaign_id=current.campaign_id,
            baseline=baseline,
            current=current,
            assessment=assessment,
            recommendations=recommendations,
        )

    def review(
        self,
        proposal: AdaptationProposal,
        decisions: Iterable[RecommendationDecision],
    ) -> AdaptationReview:
        """Record named human decisions without modifying campaign strategy."""
        if proposal.campaign_id != proposal.current.campaign_id:
            raise ValueError("proposal campaign_id does not match current measurement")
        if proposal.recommendations.campaign_id != proposal.campaign_id:
            raise ValueError("recommendation campaign_id does not match proposal")

        outcome = self.feedback_service.review(
            proposal.recommendations,
            tuple(decisions),
        )

        return AdaptationReview(
            proposal=proposal,
            outcome=outcome,
        )
