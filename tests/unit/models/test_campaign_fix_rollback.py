"""Tests for campaign fix rollback models."""

import pytest

from models.campaign_fix_rollback import CampaignFixRollback, CampaignFixRollbackPlan


def rollback(**overrides: object) -> CampaignFixRollback:
    values: dict[str, object] = {
        "source_check": "Content calendar",
        "operation": "remove-file",
        "target": "campaigns/no-lose-guard/schedule/content-calendar.md",
        "detail": "Remove the created file.",
        "safe": True,
    }
    values.update(overrides)
    return CampaignFixRollback(**values)


def test_plan_groups_safe_and_skipped_actions() -> None:
    plan = CampaignFixRollbackPlan(
        campaign_name="No Lose Guard",
        actions=(
            rollback(),
            rollback(
                source_check="Unknown",
                operation="skip",
                target=None,
                detail="Requires review.",
                safe=False,
            ),
        ),
    )

    assert len(plan.safe_actions) == 1
    assert len(plan.skipped_actions) == 1


def test_rollback_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="unsupported rollback operation"):
        rollback(operation="restore-file")


def test_safe_rollback_cannot_be_skip() -> None:
    with pytest.raises(ValueError, match="must be executable"):
        rollback(operation="skip", target=None)


def test_executable_rollback_requires_target() -> None:
    with pytest.raises(ValueError, match="target is required"):
        rollback(target=None)


def test_plan_rejects_empty_campaign_name() -> None:
    with pytest.raises(ValueError, match="campaign_name must not be empty"):
        CampaignFixRollbackPlan(campaign_name=" ", actions=())
