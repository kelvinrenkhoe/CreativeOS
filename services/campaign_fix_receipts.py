"""Persistent JSON receipts for campaign fix executions."""

import json
from dataclasses import asdict
from pathlib import Path

from models.campaign_fix_execution import CampaignFixExecutionReport, CampaignFixResult
from services.campaign import slugify


class CampaignFixReceiptError(ValueError):
    """Raised when a campaign fix receipt cannot be loaded safely."""


class JsonCampaignFixReceiptStore:
    """Save and load the latest campaign fix execution per campaign."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, campaign_name: str) -> Path:
        """Return the stable receipt path for a campaign."""
        return self.root / f"{slugify(campaign_name)}.json"

    def save(self, report: CampaignFixExecutionReport) -> Path:
        """Persist the latest fix execution report atomically."""
        path = self.path_for(report.campaign_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "campaign_name": report.campaign_name,
            "results": [asdict(result) for result in report.results],
        }
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    def load(self, campaign_name: str) -> CampaignFixExecutionReport:
        """Load the latest persisted fix execution for a campaign."""
        path = self.path_for(campaign_name)
        if not path.is_file():
            raise CampaignFixReceiptError(
                f'No campaign fix receipt found for "{campaign_name}". '
                f'Run: creativeos campaign fix "{campaign_name}"'
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CampaignFixReceiptError(f"Invalid campaign fix receipt: {exc}") from exc

        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise CampaignFixReceiptError("Unsupported campaign fix receipt format")
        if payload.get("campaign_name") != campaign_name:
            raise CampaignFixReceiptError("Campaign fix receipt name does not match request")
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise CampaignFixReceiptError("Campaign fix receipt results must be a list")

        try:
            results = tuple(CampaignFixResult(**item) for item in raw_results)
        except (TypeError, ValueError) as exc:
            raise CampaignFixReceiptError(f"Invalid campaign fix receipt result: {exc}") from exc

        return CampaignFixExecutionReport(
            campaign_name=campaign_name,
            results=results,
        )
