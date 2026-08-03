"""Tests for deterministic campaign recommendations."""

from models.doctor import DoctorCheck, DoctorReport
from services.campaign_recommendations import (
    CampaignRecommendationsService,
)


def test_failed_checks_create_recommendations() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Campaign",
                name="Release date",
                passed=False,
                detail="Release date is not configured",
            ),
            DoctorCheck(
                category="Assets",
                name="Artwork",
                passed=False,
                detail="No artwork",
                required=False,
            ),
        )
    )

    result = CampaignRecommendationsService().recommend(
        "No Lose Guard",
        report,
    )

    assert len(result.items) == 2
    assert result.items[0].source_check == "Artwork"
    assert result.items[1].source_check == "Release date"
    assert all(item.priority == 1 for item in result.items)


def test_passed_checks_do_not_create_recommendations() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Assets",
                name="Artwork",
                passed=True,
                detail="Artwork available",
                required=False,
            ),
        )
    )

    result = CampaignRecommendationsService().recommend(
        "No Lose Guard",
        report,
    )

    assert result.items == ()


def test_unknown_failed_checks_are_ignored() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Custom",
                name="Unknown check",
                passed=False,
                detail="Unknown failure",
            ),
        )
    )

    result = CampaignRecommendationsService().recommend(
        "No Lose Guard",
        report,
    )

    assert result.items == ()


def test_actions_include_campaign_slug() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Planning",
                name="Content calendar",
                passed=False,
                detail="Missing calendar",
                required=False,
            ),
        )
    )

    result = CampaignRecommendationsService().recommend(
        "No Lose Guard",
        report,
    )

    assert result.items[0].action == (
        "Complete campaigns/no-lose-guard/schedule/content-calendar.md"
    )


def test_workspace_recommendation_uses_campaign_name() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Campaign",
                name="Campaign workspace",
                passed=False,
                detail="Missing workspace",
            ),
        )
    )

    result = CampaignRecommendationsService().recommend(
        "No Lose Guard",
        report,
    )

    assert result.items[0].action == ('creativeos campaign create "No Lose Guard"')


def test_recommendations_are_ordered_by_priority() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Promotion",
                name="Radio outreach",
                passed=False,
                required=False,
            ),
            DoctorCheck(
                category="Campaign",
                name="Release date",
                passed=False,
            ),
        )
    )

    result = CampaignRecommendationsService().recommend(
        "No Lose Guard",
        report,
    )

    assert [item.priority for item in result.items] == [1, 2]
    assert result.items[0].source_check == "Release date"


def test_recommendations_are_deterministic() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(
                category="Distribution",
                name="Streaming link",
                passed=False,
                required=False,
            ),
        )
    )
    service = CampaignRecommendationsService()

    first = service.recommend("No Lose Guard", report)
    second = service.recommend("No Lose Guard", report)

    assert first == second
