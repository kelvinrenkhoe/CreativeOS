"""Tests for deterministic campaign scoring."""

from models.doctor import DoctorCheck, DoctorReport
from services.campaign_scoring import CampaignScoringService


def test_perfect_campaign_scores_one_hundred() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Campaign",
                name="Manifest",
                passed=True,
            ),
            DoctorCheck(
                category="Assets",
                name="Artwork",
                passed=True,
                required=False,
            ),
        )
    )

    score = CampaignScoringService().score(
        "No Lose Guard",
        report,
    )

    assert score.overall_score == 100
    assert score.category("Campaign").score == 100
    assert score.category("Assets").score == 100


def test_failed_checks_reduce_category_score() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Assets",
                name="Artwork",
                passed=True,
                required=False,
            ),
            DoctorCheck(
                category="Assets",
                name="Video assets",
                passed=False,
                detail="No video assets",
                required=False,
            ),
        )
    )

    score = CampaignScoringService().score(
        "No Lose Guard",
        report,
    )

    assets = score.category("Assets")

    assert assets.score == 50
    assert assets.passed_checks == 1
    assert assets.total_checks == 2
    assert assets.findings == ("Video assets: No video assets",)


def test_overall_score_is_weighted_by_check_count() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Campaign",
                name="Manifest",
                passed=True,
            ),
            DoctorCheck(
                category="Campaign",
                name="Release date",
                passed=True,
            ),
            DoctorCheck(
                category="Promotion",
                name="Press release",
                passed=False,
                required=False,
            ),
        )
    )

    score = CampaignScoringService().score(
        "No Lose Guard",
        report,
    )

    assert score.overall_score == 66
    assert score.category("Campaign").score == 100
    assert score.category("Promotion").score == 0


def test_empty_report_scores_one_hundred() -> None:
    score = CampaignScoringService().score(
        "No Lose Guard",
        DoctorReport(checks=()),
    )

    assert score.overall_score == 100
    assert score.categories == ()


def test_scoring_is_deterministic() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Distribution",
                name="Streaming link",
                passed=False,
                detail="No streaming link",
                required=False,
            ),
        )
    )
    service = CampaignScoringService()

    first = service.score("No Lose Guard", report)
    second = service.score("No Lose Guard", report)

    assert first == second
