"""Tests for persistent campaign fix receipts."""

import json
from pathlib import Path

import pytest

from models.campaign_fix_execution import CampaignFixExecutionReport, CampaignFixResult
from services.campaign_fix_receipts import (
    CampaignFixReceiptError,
    JsonCampaignFixReceiptStore,
)


def report() -> CampaignFixExecutionReport:
    return CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            CampaignFixResult(
                source_check="Content calendar",
                operation="create-file",
                target="campaigns/no-lose-guard/schedule/content-calendar.md",
                status="applied",
                detail="Created template.",
            ),
        ),
    )


def test_store_round_trips_latest_report(tmp_path: Path) -> None:
    store = JsonCampaignFixReceiptStore(tmp_path)

    path = store.save(report())

    assert path == tmp_path / "no-lose-guard.json"
    assert store.load("No Lose Guard") == report()


def test_store_replaces_previous_receipt(tmp_path: Path) -> None:
    store = JsonCampaignFixReceiptStore(tmp_path)
    first = report()
    second = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(),
    )

    store.save(first)
    store.save(second)

    assert store.load("No Lose Guard") == second


def test_missing_receipt_has_actionable_error(tmp_path: Path) -> None:
    store = JsonCampaignFixReceiptStore(tmp_path)

    with pytest.raises(CampaignFixReceiptError, match="creativeos campaign fix"):
        store.load("Missing Campaign")


def test_invalid_receipt_is_rejected(tmp_path: Path) -> None:
    store = JsonCampaignFixReceiptStore(tmp_path)
    path = store.path_for("No Lose Guard")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")

    with pytest.raises(CampaignFixReceiptError, match="Unsupported"):
        store.load("No Lose Guard")
