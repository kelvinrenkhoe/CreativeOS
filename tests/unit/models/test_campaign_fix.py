"""Tests for campaign fix plan models."""

import pytest

from models.campaign_fix import CampaignFix, CampaignFixPlan


def fix(
    *,
    kind: str = "automatic",
    operation: str = "create-file",
) -> CampaignFix:
    return CampaignFix(
        category="Planning",
        source_check="Content calendar",
        title="Create a campaign content calendar",
        kind=kind,
        operation=operation,
        target="campaigns/no-lose-guard/schedule/content-calendar.md",
        detail="Create the standard template.",
        priority=1,
    )


def test_fix_plan_classifies_items() -> None:
    plan = CampaignFixPlan(
        campaign_name="No Lose Guard",
        fixes=(
            fix(),
            fix(kind="manual", operation="update-configuration"),
            fix(kind="unsupported", operation="unsupported"),
        ),
    )

    assert len(plan.automatic) == 1
    assert len(plan.manual) == 1
    assert len(plan.unsupported) == 1


@pytest.mark.parametrize("kind", ["", "unsafe"])
def test_fix_rejects_invalid_kind(kind: str) -> None:
    with pytest.raises(ValueError, match="kind must be one of"):
        fix(kind=kind)


def test_fix_rejects_invalid_operation() -> None:
    with pytest.raises(ValueError, match="unsupported fix operation"):
        fix(operation="delete-everything")


@pytest.mark.parametrize("priority", [0, 4])
def test_fix_rejects_invalid_priority(priority: int) -> None:
    with pytest.raises(ValueError, match="priority must be between 1 and 3"):
        CampaignFix(
            category="Planning",
            source_check="Content calendar",
            title="Create calendar",
            kind="automatic",
            operation="create-file",
            target=None,
            detail="Create a template.",
            priority=priority,
        )


def test_plan_rejects_empty_campaign_name() -> None:
    with pytest.raises(ValueError, match="campaign_name must not be empty"):
        CampaignFixPlan(campaign_name=" ", fixes=())
