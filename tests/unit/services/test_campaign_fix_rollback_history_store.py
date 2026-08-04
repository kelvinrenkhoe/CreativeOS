"""Tests for append-only campaign rollback history storage."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from models.campaign_fix_rollback_execution import (
    CampaignFixRollbackExecutionReport,
    CampaignFixRollbackResult,
)
from models.campaign_fix_rollback_history import CampaignFixRollbackHistoryRecord
from services.campaign_fix_rollback_history import (
    CampaignFixRollbackHistoryError,
    JsonCampaignFixRollbackHistoryStore,
)


def record(executed_at: datetime) -> CampaignFixRollbackHistoryRecord:
    report = CampaignFixRollbackExecutionReport(
        campaign_name="No Lose Guard",
        dry_run=False,
        results=(
            CampaignFixRollbackResult(
                source_check="Content calendar",
                operation="remove-file",
                target="campaigns/no-lose-guard/content-calendar.md",
                status="removed",
                detail="Removed file.",
            ),
        ),
    )
    return CampaignFixRollbackHistoryRecord.from_report(
        report,
        executed_at=executed_at,
    )


def test_append_and_load_round_trip(tmp_path: Path) -> None:
    store = JsonCampaignFixRollbackHistoryStore(tmp_path)
    expected = record(datetime(2026, 8, 4, 8, 30, tzinfo=UTC))

    path = store.append(expected)
    actual = store.load(expected.campaign_name, expected.execution_id)

    assert path.is_file()
    assert actual == expected


def test_list_returns_newest_first(tmp_path: Path) -> None:
    store = JsonCampaignFixRollbackHistoryStore(tmp_path)
    first = record(datetime(2026, 8, 4, 8, 30, tzinfo=UTC))
    second = record(first.executed_at + timedelta(minutes=5))
    store.append(first)
    store.append(second)

    assert store.list("No Lose Guard") == (second, first)


def test_append_does_not_replace_existing_record(tmp_path: Path) -> None:
    store = JsonCampaignFixRollbackHistoryStore(tmp_path)
    expected = record(datetime(2026, 8, 4, 8, 30, tzinfo=UTC))
    store.append(expected)

    with pytest.raises(CampaignFixRollbackHistoryError, match="already exists"):
        store.append(expected)


def test_list_missing_campaign_returns_empty_tuple(tmp_path: Path) -> None:
    store = JsonCampaignFixRollbackHistoryStore(tmp_path)

    assert store.list("Missing Campaign") == ()
