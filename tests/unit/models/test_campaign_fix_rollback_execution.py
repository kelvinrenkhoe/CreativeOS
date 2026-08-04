"""Tests for campaign fix rollback execution models."""

import pytest

from models.campaign_fix_rollback_execution import (
    CampaignFixRollbackExecutionReport,
    CampaignFixRollbackResult,
)


def result(status: str) -> CampaignFixRollbackResult:
    return CampaignFixRollbackResult(
        source_check="Content calendar",
        operation="remove-file",
        target="campaigns/no-lose-guard/schedule/content-calendar.md",
        status=status,
        detail="Rollback result.",
    )


def test_report_groups_execution_statuses() -> None:
    report = CampaignFixRollbackExecutionReport(
        campaign_name="No Lose Guard",
        dry_run=False,
        results=(
            result("removed"),
            result("would-remove"),
            result("missing"),
            result("skipped"),
        ),
    )

    assert len(report.removed) == 1
    assert len(report.would_remove) == 1
    assert len(report.missing) == 1
    assert len(report.skipped) == 1


def test_result_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="status must be one of"):
        result("unknown")


def test_report_requires_campaign_name() -> None:
    with pytest.raises(ValueError, match="campaign_name"):
        CampaignFixRollbackExecutionReport(
            campaign_name=" ",
            dry_run=False,
            results=(),
        )
