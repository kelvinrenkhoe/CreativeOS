import pytest

from services.campaign_measurement import CampaignMeasurement, CampaignMetricSummary
from services.campaign_planner import CampaignIntent, CampaignPlan
from services.cross_campaign_learning import (
    CompletedCampaignOutcome,
    CrossCampaignLearningService,
)
from services.recommendation_feedback import FeedbackOutcome, StrategyRecommendation


def plan(work_id: str, objective: str = "build awareness") -> CampaignPlan:
    return CampaignPlan(
        work_id=work_id,
        work_name=work_id.replace("-", " ").title(),
        total_weeks=4,
        intent=CampaignIntent(
            objective=objective,
            audience="afrobeats listeners",
            tone="cinematic",
            platforms=("instagram",),
        ),
        phases=(),
    )


def recommendation(kind: str = "refresh-visual-direction") -> StrategyRecommendation:
    return StrategyRecommendation(
        id="recommendation-001",
        kind=kind,
        priority="medium",
        action="Refresh the visual direction",
        reason="visual repetition detected",
        signal_kind="visual-repetition",
    )


def outcome(
    campaign_id: str,
    *,
    views: float,
    objective: str = "build awareness",
    accepted: tuple[StrategyRecommendation, ...] = (),
) -> CompletedCampaignOutcome:
    measurement = CampaignMeasurement(
        campaign_id=campaign_id,
        asset_ids=(f"{campaign_id}-poster",),
        metrics=(
            CampaignMetricSummary(
                platform="instagram",
                metric="views",
                value=views,
                asset_count=1,
                publication_count=1,
                latest_observed_at="2026-07-26T12:00:00+00:00",
            ),
        ),
    )
    feedback = FeedbackOutcome(
        campaign_id=campaign_id,
        accepted=accepted,
        rejected=(),
        pending=(),
    )
    return CompletedCampaignOutcome(
        campaign_id=campaign_id,
        plan=plan(campaign_id, objective),
        measurement=measurement,
        feedback=feedback,
    )


def test_builds_metric_benchmark_for_matching_campaign_context() -> None:
    result = CrossCampaignLearningService().learn(
        [
            outcome("campaign-a", views=100),
            outcome("campaign-b", views=300),
        ]
    )

    benchmark = result.metric_benchmarks[0]
    assert benchmark.average_value == 200
    assert benchmark.evidence_count == 2
    assert benchmark.campaign_ids == ("campaign-a", "campaign-b")
    assert benchmark.objective == "build awareness"
    assert benchmark.platform == "instagram"
    assert benchmark.metric == "views"
    assert result.has_patterns is True


def test_does_not_combine_different_campaign_intents() -> None:
    result = CrossCampaignLearningService().learn(
        [
            outcome("campaign-a", views=100),
            outcome("campaign-b", views=300, objective="drive streams"),
        ]
    )

    assert result.metric_benchmarks == ()
    assert result.has_patterns is False


def test_identifies_strategy_accepted_across_campaigns() -> None:
    accepted = (recommendation(),)
    result = CrossCampaignLearningService().learn(
        [
            outcome("campaign-b", views=200, accepted=accepted),
            outcome("campaign-a", views=100, accepted=accepted),
        ]
    )

    pattern = result.accepted_strategy_patterns[0]
    assert pattern.kind == "refresh-visual-direction"
    assert pattern.evidence_count == 2
    assert pattern.campaign_ids == ("campaign-a", "campaign-b")
    assert pattern.action_examples == ("Refresh the visual direction",)


def test_filters_patterns_below_configured_evidence_threshold() -> None:
    result = CrossCampaignLearningService().learn(
        [
            outcome("campaign-a", views=100, accepted=(recommendation(),)),
            outcome("campaign-b", views=200, accepted=(recommendation(),)),
        ],
        minimum_evidence=3,
    )

    assert result.metric_benchmarks == ()
    assert result.accepted_strategy_patterns == ()


def test_returns_empty_learning_for_no_completed_campaigns() -> None:
    result = CrossCampaignLearningService().learn([])

    assert result.campaign_ids == ()
    assert result.has_patterns is False


@pytest.mark.parametrize("minimum_evidence", [0, 1])
def test_requires_repeated_evidence(minimum_evidence: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        CrossCampaignLearningService().learn([], minimum_evidence=minimum_evidence)


def test_rejects_duplicate_campaigns() -> None:
    completed = outcome("campaign-a", views=100)

    with pytest.raises(ValueError, match="duplicate campaign_id"):
        CrossCampaignLearningService().learn([completed, completed])


def test_rejects_mismatched_measurement_campaign() -> None:
    completed = outcome("campaign-a", views=100)
    invalid = CompletedCampaignOutcome(
        campaign_id="campaign-b",
        plan=completed.plan,
        measurement=completed.measurement,
        feedback=FeedbackOutcome(
            campaign_id="campaign-b",
            accepted=(),
            rejected=(),
            pending=(),
        ),
    )

    with pytest.raises(ValueError, match="measurement campaign_id"):
        CrossCampaignLearningService().learn([invalid])
