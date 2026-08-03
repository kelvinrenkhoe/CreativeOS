"""Tests for campaign fix execution result models."""

import pytest

from models.campaign_fix_execution import (
    CampaignFixExecutionReport,
    CampaignFixResult,
)


def result(status: str = "applied") -> CampaignFixResult:
    return CampaignFixResult(
        source_check="Artwork",
        operation="ensure-directory",
        target="campaigns/no-lose-guard/assets/artwork",
        status=status,
        detail="Completed safely.",
    )


def test_execution_report_groups_results_by_status() -> None:
    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            result("applied"),
            result("already-present"),
            result("skipped"),
        ),
    )

    assert len(report.applied) == 1
    assert len(report.already_present) == 1
    assert len(report.skipped) == 1


@pytest.mark.parametrize("status", ["failed", "pending", ""])
def test_fix_result_rejects_invalid_status(status: str) -> None:
    with pytest.raises(ValueError, match="status must be one of"):
        result(status)


def test_execution_report_rejects_empty_campaign_name() -> None:
    with pytest.raises(ValueError, match="campaign_name must not be empty"):
        CampaignFixExecutionReport(campaign_name=" ", results=())
