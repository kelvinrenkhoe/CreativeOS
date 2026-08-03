"""Tests for campaign recommendation models."""

import pytest

from models.campaign_recommendation import (
    CampaignRecommendation,
    CampaignRecommendations,
)


def recommendation(
    *,
    impact: str = "high",
    priority: int = 1,
    action: str | None = "Do something",
) -> CampaignRecommendation:
    return CampaignRecommendation(
        category="Assets",
        source_check="Artwork",
        title="Add artwork",
        detail="Final artwork is required.",
        action=action,
        impact=impact,
        priority=priority,
    )


def test_recommendation_collection_counts_items() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(
            recommendation(),
            recommendation(
                impact="medium",
                priority=2,
                action=None,
            ),
        ),
    )

    assert recommendations.high_impact_count == 1
    assert recommendations.actionable_count == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("category", " ", "category must not be empty"),
        ("source_check", "", "source_check must not be empty"),
        ("title", " ", "title must not be empty"),
        ("detail", "", "detail must not be empty"),
    ],
)
def test_recommendation_rejects_empty_text_fields(
    field: str,
    value: str,
    message: str,
) -> None:
    values = {
        "category": "Assets",
        "source_check": "Artwork",
        "title": "Add artwork",
        "detail": "Final artwork is required.",
        "action": "Do something",
        "impact": "high",
        "priority": 1,
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        CampaignRecommendation(**values)


def test_recommendation_rejects_invalid_impact() -> None:
    with pytest.raises(
        ValueError,
        match="impact must be one of",
    ):
        recommendation(impact="urgent")


@pytest.mark.parametrize("priority", [0, 4])
def test_recommendation_rejects_invalid_priority(
    priority: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="priority must be between 1 and 3",
    ):
        recommendation(priority=priority)


def test_collection_rejects_empty_campaign_name() -> None:
    with pytest.raises(
        ValueError,
        match="campaign_name must not be empty",
    ):
        CampaignRecommendations(
            campaign_name=" ",
            items=(),
        )
