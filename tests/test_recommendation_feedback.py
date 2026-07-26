import pytest

from services.fatigue_signals import FatigueAssessment, FatigueSignal
from services.recommendation_feedback import (
    RecommendationDecision,
    RecommendationFeedbackService,
)


def assessment(*signals: FatigueSignal) -> FatigueAssessment:
    return FatigueAssessment(campaign_id="no-way-back", signals=signals)


def performance_signal(severity: str = "moderate") -> FatigueSignal:
    return FatigueSignal(
        kind="performance-decline",
        severity=severity,
        score=0.25,
        platform="instagram",
        metric="views",
        reason="instagram views declined 25.0% from the baseline",
    )


def repetition_signal(medium: str, asset_id: str, severity: str = "moderate") -> FatigueSignal:
    return FatigueSignal(
        kind=f"{medium}-repetition",
        severity=severity,
        score=0.8,
        asset_id=asset_id,
        medium=medium,
        reason=f"{medium} pattern is 80.0% similar to a prior campaign asset",
    )


def test_recommends_evidence_based_strategy_adjustments() -> None:
    result = RecommendationFeedbackService().recommend(
        assessment(
            repetition_signal("content", "caption-2"),
            performance_signal("high"),
            repetition_signal("visual", "poster-2"),
        )
    )

    assert result.campaign_id == "no-way-back"
    assert result.requires_review is True
    assert tuple((item.id, item.kind, item.priority) for item in result.recommendations) == (
        ("recommendation-001", "rotate-content-pattern", "medium"),
        ("recommendation-002", "review-platform-strategy", "high"),
        ("recommendation-003", "refresh-visual-direction", "medium"),
    )
    assert result.recommendations[1].platform == "instagram"
    assert result.recommendations[1].metric == "views"


def test_returns_no_recommendations_without_fatigue() -> None:
    result = RecommendationFeedbackService().recommend(assessment())

    assert result.recommendations == ()
    assert result.requires_review is False


def test_records_accepted_rejected_and_pending_decisions() -> None:
    service = RecommendationFeedbackService()
    recommendations = service.recommend(
        assessment(
            repetition_signal("content", "caption-2"),
            performance_signal(),
            repetition_signal("visual", "poster-2"),
        )
    )

    outcome = service.review(
        recommendations,
        [
            RecommendationDecision("recommendation-001", "accept", "Kelvin"),
            RecommendationDecision(
                "recommendation-002",
                "reject",
                "Kelvin",
                "The campaign has insufficient baseline data",
            ),
        ],
    )

    assert tuple(item.id for item in outcome.accepted) == ("recommendation-001",)
    assert tuple(item.id for item in outcome.rejected) == ("recommendation-002",)
    assert tuple(item.id for item in outcome.pending) == ("recommendation-003",)


@pytest.mark.parametrize("decision", ["", "approve", "decline"])
def test_rejects_invalid_decisions(decision: str) -> None:
    recommendations = RecommendationFeedbackService().recommend(assessment(performance_signal()))

    with pytest.raises(ValueError, match="decision"):
        RecommendationFeedbackService().review(
            recommendations,
            [RecommendationDecision("recommendation-001", decision, "Kelvin")],
        )


def test_rejects_unknown_recommendation() -> None:
    recommendations = RecommendationFeedbackService().recommend(assessment(performance_signal()))

    with pytest.raises(ValueError, match="unknown recommendation_id"):
        RecommendationFeedbackService().review(
            recommendations,
            [RecommendationDecision("recommendation-999", "accept", "Kelvin")],
        )


def test_rejects_duplicate_decisions() -> None:
    recommendations = RecommendationFeedbackService().recommend(assessment(performance_signal()))
    decision = RecommendationDecision("recommendation-001", "accept", "Kelvin")

    with pytest.raises(ValueError, match="duplicate decision"):
        RecommendationFeedbackService().review(recommendations, [decision, decision])


def test_requires_named_human_review() -> None:
    recommendations = RecommendationFeedbackService().recommend(assessment(performance_signal()))

    with pytest.raises(ValueError, match="decided_by"):
        RecommendationFeedbackService().review(
            recommendations,
            [RecommendationDecision("recommendation-001", "accept", "")],
        )


def test_rejects_unsupported_signal_kind() -> None:
    unsupported = FatigueSignal(
        kind="unknown",
        severity="moderate",
        score=0.5,
        reason="unsupported evidence",
    )

    with pytest.raises(ValueError, match="unsupported fatigue signal"):
        RecommendationFeedbackService().recommend(assessment(unsupported))
