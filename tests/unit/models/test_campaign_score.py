"""Tests for campaign score models."""

import pytest

from models.campaign_score import CampaignScore, CampaignScoreCategory


def test_campaign_score_returns_named_category() -> None:
    release = CampaignScoreCategory(
        name="Campaign",
        score=100,
        passed_checks=3,
        total_checks=3,
    )
    score = CampaignScore(
        campaign_name="No Lose Guard",
        overall_score=100,
        categories=(release,),
    )

    assert score.category("Campaign") is release


def test_campaign_score_rejects_unknown_category() -> None:
    score = CampaignScore(
        campaign_name="No Lose Guard",
        overall_score=100,
        categories=(),
    )

    with pytest.raises(
        KeyError,
        match="Unknown campaign score category",
    ):
        score.category("Promotion")


@pytest.mark.parametrize("value", [-1, 101])
def test_category_rejects_invalid_score(value: int) -> None:
    with pytest.raises(
        ValueError,
        match="category score must be between 0 and 100",
    ):
        CampaignScoreCategory(
            name="Campaign",
            score=value,
            passed_checks=0,
            total_checks=0,
        )


def test_campaign_score_rejects_empty_campaign_name() -> None:
    with pytest.raises(
        ValueError,
        match="campaign_name must not be empty",
    ):
        CampaignScore(
            campaign_name=" ",
            overall_score=100,
            categories=(),
        )
