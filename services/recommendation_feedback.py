"""Turn fatigue evidence into deterministic, human-reviewed strategy recommendations."""

from collections.abc import Iterable
from dataclasses import dataclass

from services.fatigue_signals import FatigueAssessment, FatigueSignal


@dataclass(frozen=True, slots=True)
class StrategyRecommendation:
    """One evidence-based campaign adjustment proposed for human review."""

    id: str
    kind: str
    priority: str
    action: str
    reason: str
    signal_kind: str
    asset_id: str | None = None
    platform: str | None = None
    metric: str | None = None


@dataclass(frozen=True, slots=True)
class RecommendationSet:
    """Ordered strategy recommendations for one measured campaign."""

    campaign_id: str
    recommendations: tuple[StrategyRecommendation, ...]

    @property
    def requires_review(self) -> bool:
        """Return whether any proposed recommendation needs a decision."""
        return bool(self.recommendations)


@dataclass(frozen=True, slots=True)
class RecommendationDecision:
    """A named human's decision for one exact recommendation."""

    recommendation_id: str
    decision: str
    decided_by: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class FeedbackOutcome:
    """Accepted, rejected, and pending recommendations after human review."""

    campaign_id: str
    accepted: tuple[StrategyRecommendation, ...]
    rejected: tuple[StrategyRecommendation, ...]
    pending: tuple[StrategyRecommendation, ...]


class RecommendationFeedbackService:
    """Create explainable proposals and record decisions without applying changes."""

    def recommend(self, assessment: FatigueAssessment) -> RecommendationSet:
        """Translate ordered fatigue evidence into deterministic strategy proposals."""
        recommendations = tuple(
            self._recommendation(index, signal)
            for index, signal in enumerate(assessment.signals, start=1)
        )
        return RecommendationSet(
            campaign_id=self._required(assessment.campaign_id, "campaign_id"),
            recommendations=recommendations,
        )

    def review(
        self,
        recommendations: RecommendationSet,
        decisions: Iterable[RecommendationDecision],
    ) -> FeedbackOutcome:
        """Validate human decisions and classify every recommendation."""
        by_id = {item.id: item for item in recommendations.recommendations}
        normalized: dict[str, str] = {}

        for decision in decisions:
            recommendation_id = self._required(
                decision.recommendation_id,
                "recommendation_id",
            )
            if recommendation_id not in by_id:
                raise ValueError(f"unknown recommendation_id: {recommendation_id}")
            if recommendation_id in normalized:
                raise ValueError(f"duplicate decision for recommendation_id: {recommendation_id}")

            value = self._required(decision.decision, "decision").casefold()
            if value not in {"accept", "reject"}:
                raise ValueError("decision must be accept or reject")
            self._required(decision.decided_by, "decided_by")
            if decision.reason is not None:
                self._required(decision.reason, "reason")
            normalized[recommendation_id] = value

        return FeedbackOutcome(
            campaign_id=recommendations.campaign_id,
            accepted=tuple(
                item for item in recommendations.recommendations if normalized.get(item.id) == "accept"
            ),
            rejected=tuple(
                item for item in recommendations.recommendations if normalized.get(item.id) == "reject"
            ),
            pending=tuple(
                item for item in recommendations.recommendations if item.id not in normalized
            ),
        )

    @classmethod
    def _recommendation(
        cls,
        index: int,
        signal: FatigueSignal,
    ) -> StrategyRecommendation:
        if signal.kind == "performance-decline":
            platform = cls._required(signal.platform or "", "platform")
            metric = cls._required(signal.metric or "", "metric")
            kind = "review-platform-strategy"
            action = f"Review and adjust the {platform} {metric} strategy"
        elif signal.kind == "content-repetition":
            kind = "rotate-content-pattern"
            action = f"Rotate the content pattern for {cls._required(signal.asset_id or '', 'asset_id')}"
        elif signal.kind == "visual-repetition":
            kind = "refresh-visual-direction"
            action = f"Refresh the visual direction for {cls._required(signal.asset_id or '', 'asset_id')}"
        else:
            raise ValueError(f"unsupported fatigue signal kind: {signal.kind}")

        return StrategyRecommendation(
            id=f"recommendation-{index:03d}",
            kind=kind,
            priority="high" if signal.severity == "high" else "medium",
            action=action,
            reason=cls._required(signal.reason, "reason"),
            signal_kind=signal.kind,
            asset_id=signal.asset_id,
            platform=signal.platform,
            metric=signal.metric,
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
