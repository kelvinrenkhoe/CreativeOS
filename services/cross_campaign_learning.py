"""Identify reusable evidence-backed patterns across completed campaigns."""

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean

from services.campaign_measurement import CampaignMeasurement
from services.campaign_planner import CampaignPlan
from services.recommendation_feedback import FeedbackOutcome, StrategyRecommendation


@dataclass(frozen=True, slots=True)
class CompletedCampaignOutcome:
    """The reviewed evidence available after one campaign completes."""

    campaign_id: str
    plan: CampaignPlan
    measurement: CampaignMeasurement
    feedback: FeedbackOutcome


@dataclass(frozen=True, slots=True)
class MetricBenchmark:
    """An observed metric benchmark for one matching campaign context."""

    objective: str
    audience: str
    tone: str
    platform: str
    metric: str
    average_value: float
    evidence_count: int
    campaign_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcceptedStrategyPattern:
    """A strategy adjustment accepted in multiple completed campaigns."""

    kind: str
    platform: str | None
    metric: str | None
    evidence_count: int
    campaign_ids: tuple[str, ...]
    action_examples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrossCampaignLearning:
    """Advisory patterns derived from completed campaign evidence."""

    campaign_ids: tuple[str, ...]
    metric_benchmarks: tuple[MetricBenchmark, ...]
    accepted_strategy_patterns: tuple[AcceptedStrategyPattern, ...]

    @property
    def has_patterns(self) -> bool:
        """Return whether sufficient repeated evidence produced any learning."""
        return bool(self.metric_benchmarks or self.accepted_strategy_patterns)


class CrossCampaignLearningService:
    """Learn across campaigns without changing plans or strategy automatically."""

    def learn(
        self,
        outcomes: Iterable[CompletedCampaignOutcome],
        *,
        minimum_evidence: int = 2,
    ) -> CrossCampaignLearning:
        """Return deterministic patterns supported by enough completed campaigns."""
        if minimum_evidence < 2:
            raise ValueError("minimum_evidence must be at least 2")

        completed = tuple(outcomes)
        campaign_ids = tuple(sorted(self._validate_outcomes(completed)))
        benchmarks = self._metric_benchmarks(completed, minimum_evidence)
        strategies = self._accepted_strategies(completed, minimum_evidence)
        return CrossCampaignLearning(
            campaign_ids=campaign_ids,
            metric_benchmarks=benchmarks,
            accepted_strategy_patterns=strategies,
        )

    @classmethod
    def _validate_outcomes(
        cls,
        outcomes: tuple[CompletedCampaignOutcome, ...],
    ) -> set[str]:
        campaign_ids: set[str] = set()
        for outcome in outcomes:
            campaign_id = cls._required(outcome.campaign_id, "campaign_id")
            if campaign_id in campaign_ids:
                raise ValueError(f"duplicate campaign_id: {campaign_id}")
            if outcome.measurement.campaign_id != campaign_id:
                raise ValueError("measurement campaign_id must match outcome campaign_id")
            if outcome.feedback.campaign_id != campaign_id:
                raise ValueError("feedback campaign_id must match outcome campaign_id")
            campaign_ids.add(campaign_id)
        return campaign_ids

    @classmethod
    def _metric_benchmarks(
        cls,
        outcomes: tuple[CompletedCampaignOutcome, ...],
        minimum_evidence: int,
    ) -> tuple[MetricBenchmark, ...]:
        grouped: dict[tuple[str, str, str, str, str], list[tuple[str, float]]] = {}
        for outcome in outcomes:
            intent = outcome.plan.intent
            for summary in outcome.measurement.metrics:
                key = (
                    intent.objective,
                    intent.audience,
                    intent.tone,
                    summary.platform,
                    summary.metric,
                )
                grouped.setdefault(key, []).append((outcome.campaign_id, summary.value))

        return tuple(
            MetricBenchmark(
                objective=key[0],
                audience=key[1],
                tone=key[2],
                platform=key[3],
                metric=key[4],
                average_value=fmean(value for _, value in evidence),
                evidence_count=len(evidence),
                campaign_ids=tuple(sorted(campaign_id for campaign_id, _ in evidence)),
            )
            for key, evidence in sorted(grouped.items())
            if len(evidence) >= minimum_evidence
        )

    @classmethod
    def _accepted_strategies(
        cls,
        outcomes: tuple[CompletedCampaignOutcome, ...],
        minimum_evidence: int,
    ) -> tuple[AcceptedStrategyPattern, ...]:
        grouped: dict[
            tuple[str, str | None, str | None],
            list[tuple[str, StrategyRecommendation]],
        ] = {}
        for outcome in outcomes:
            for recommendation in outcome.feedback.accepted:
                key = (
                    cls._required(recommendation.kind, "recommendation kind"),
                    recommendation.platform,
                    recommendation.metric,
                )
                grouped.setdefault(key, []).append((outcome.campaign_id, recommendation))

        return tuple(
            AcceptedStrategyPattern(
                kind=key[0],
                platform=key[1],
                metric=key[2],
                evidence_count=len({campaign_id for campaign_id, _ in evidence}),
                campaign_ids=tuple(sorted({campaign_id for campaign_id, _ in evidence})),
                action_examples=tuple(sorted({item.action for _, item in evidence})),
            )
            for key, evidence in sorted(
                grouped.items(),
                key=lambda item: tuple(value or "" for value in item[0]),
            )
            if len({campaign_id for campaign_id, _ in evidence}) >= minimum_evidence
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
