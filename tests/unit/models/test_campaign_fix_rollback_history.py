"""Tests for campaign rollback history records."""

from datetime import UTC, datetime

import pytest

from models.campaign_fix_rollback_execution import CampaignFixRollbackExecutionReport
from models.campaign_fix_rollback_history import CampaignFixRollbackHistoryRecord


def report() -> CampaignFixRollbackExecutionReport:
    return CampaignFixRollbackExecutionReport(
        campaign_name="No Lose Guard",
        dry_run=False,
        results=(),
    )


def test_record_from_report_uses_utc_timestamp() -> None:
    executed_at = datetime(2026, 8, 4, 8, 30, tzinfo=UTC)

    record = CampaignFixRollbackHistoryRecord.from_report(
        report(),
        executed_at=executed_at,
    )

    assert record.execution_id == "rb-20260804T083000000000Z"
    assert record.executed_at == executed_at
    assert record.campaign_name == "No Lose Guard"


def test_record_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        CampaignFixRollbackHistoryRecord(
            execution_id="rb-1",
            campaign_name="No Lose Guard",
            executed_at=datetime(2026, 8, 4, 8, 30),
            report=report(),
        )


def test_record_requires_matching_campaign_name() -> None:
    with pytest.raises(ValueError, match="must match"):
        CampaignFixRollbackHistoryRecord(
            execution_id="rb-1",
            campaign_name="Different Campaign",
            executed_at=datetime.now(UTC),
            report=report(),
        )
