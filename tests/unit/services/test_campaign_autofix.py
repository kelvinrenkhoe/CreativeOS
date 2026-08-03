"""Tests for the plan-only campaign auto-fix planner."""

from models.campaign_recommendation import (
    CampaignRecommendation,
    CampaignRecommendations,
)
from services.campaign_autofix import CampaignAutoFixPlanner


def recommendation(
    source_check: str,
    *,
    category: str = "Campaign",
    priority: int = 1,
    action: str | None = None,
) -> CampaignRecommendation:
    return CampaignRecommendation(
        category=category,
        source_check=source_check,
        title=f"Fix {source_check}",
        detail=f"Resolve {source_check}.",
        action=action,
        impact="high" if priority == 1 else "medium",
        priority=priority,
    )


def test_planner_classifies_automatic_and_manual_fixes() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(
            recommendation("Content calendar", category="Planning"),
            recommendation("Release date"),
        ),
    )

    plan = CampaignAutoFixPlanner().plan(recommendations)

    assert len(plan.automatic) == 1
    assert plan.automatic[0].operation == "create-file"
    assert plan.automatic[0].target == ("campaigns/no-lose-guard/schedule/content-calendar.md")
    assert len(plan.manual) == 1
    assert plan.manual[0].operation == "update-configuration"


def test_planner_marks_unknown_recommendation_unsupported() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(recommendation("Custom check"),),
    )

    plan = CampaignAutoFixPlanner().plan(recommendations)

    assert len(plan.unsupported) == 1
    assert plan.unsupported[0].operation == "unsupported"
    assert plan.unsupported[0].target is None


def test_workspace_fix_reuses_recommendation_action() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(
            recommendation(
                "Campaign workspace",
                action='creativeos campaign create "No Lose Guard"',
            ),
        ),
    )

    plan = CampaignAutoFixPlanner().plan(recommendations)

    assert plan.automatic[0].operation == "run-command"
    assert plan.automatic[0].target == ('creativeos campaign create "No Lose Guard"')


def test_planner_orders_by_priority_then_fix_kind() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(
            recommendation("Radio outreach", priority=2),
            recommendation("Release date", priority=1),
            recommendation("Campaign manifest", priority=1),
            recommendation("Artwork", category="Assets", priority=1),
        ),
    )

    plan = CampaignAutoFixPlanner().plan(recommendations)

    assert [fix.source_check for fix in plan.fixes] == [
        "Artwork",
        "Release date",
        "Campaign manifest",
        "Radio outreach",
    ]


def test_planner_is_deterministic() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(recommendation("Video assets", category="Assets"),),
    )
    planner = CampaignAutoFixPlanner()

    assert planner.plan(recommendations) == planner.plan(recommendations)


def test_empty_recommendations_produce_empty_plan() -> None:
    recommendations = CampaignRecommendations(
        campaign_name="No Lose Guard",
        items=(),
    )

    plan = CampaignAutoFixPlanner().plan(recommendations)

    assert plan.fixes == ()
    assert plan.automatic == ()
    assert plan.manual == ()
    assert plan.unsupported == ()
