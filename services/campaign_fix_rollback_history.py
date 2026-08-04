"""Append-only JSON storage for campaign rollback execution history."""

import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from models.campaign_fix_rollback import slugify
from models.campaign_fix_rollback_execution import (
    CampaignFixRollbackExecutionReport,
    CampaignFixRollbackResult,
)
from models.campaign_fix_rollback_history import CampaignFixRollbackHistoryRecord


class CampaignFixRollbackHistoryError(ValueError):
    """Raised when rollback history cannot be loaded or validated."""


class JsonCampaignFixRollbackHistoryStore:
    """Persist immutable rollback execution records as individual JSON files."""

    VERSION = 1

    def __init__(self, root: Path) -> None:
        self.root = root

    def append(self, record: CampaignFixRollbackHistoryRecord) -> Path:
        """Persist one history record without replacing earlier executions."""
        directory = self.root / slugify(record.campaign_name)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{record.execution_id}.json"
        if path.exists():
            raise CampaignFixRollbackHistoryError(
                f"Rollback history record already exists: {record.execution_id}"
            )

        payload = self._serialize(record)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            prefix=f".{record.execution_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary_path = Path(handle.name)

        os.replace(temporary_path, path)
        return path

    def list(self, campaign_name: str) -> tuple[CampaignFixRollbackHistoryRecord, ...]:
        """Return campaign rollback records newest first."""
        directory = self.root / slugify(campaign_name)
        if not directory.exists():
            return ()

        records = tuple(self._load(path) for path in sorted(directory.glob("rb-*.json")))
        return tuple(sorted(records, key=lambda record: record.executed_at, reverse=True))

    def load(
        self,
        campaign_name: str,
        execution_id: str,
    ) -> CampaignFixRollbackHistoryRecord:
        """Load one rollback execution record by ID."""
        path = self.root / slugify(campaign_name) / f"{execution_id}.json"
        if not path.is_file():
            raise CampaignFixRollbackHistoryError(
                f"No rollback history record found: {execution_id}"
            )
        return self._load(path)

    def _load(self, path: Path) -> CampaignFixRollbackHistoryRecord:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return self._deserialize(payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CampaignFixRollbackHistoryError(
                f"Invalid rollback history record: {path}"
            ) from exc

    @classmethod
    def _serialize(cls, record: CampaignFixRollbackHistoryRecord) -> dict[str, object]:
        return {
            "version": cls.VERSION,
            "execution_id": record.execution_id,
            "campaign_name": record.campaign_name,
            "executed_at": record.executed_at.isoformat(),
            "report": {
                "campaign_name": record.report.campaign_name,
                "dry_run": record.report.dry_run,
                "results": [
                    {
                        "source_check": result.source_check,
                        "operation": result.operation,
                        "target": result.target,
                        "status": result.status,
                        "detail": result.detail,
                    }
                    for result in record.report.results
                ],
            },
        }

    @classmethod
    def _deserialize(cls, payload: dict[str, object]) -> CampaignFixRollbackHistoryRecord:
        if payload["version"] != cls.VERSION:
            raise CampaignFixRollbackHistoryError("Unsupported rollback history version")

        report_payload = payload["report"]
        if not isinstance(report_payload, dict):
            raise CampaignFixRollbackHistoryError("Invalid rollback history report")

        raw_results = report_payload["results"]
        if not isinstance(raw_results, list):
            raise CampaignFixRollbackHistoryError("Invalid rollback history results")

        results = tuple(
            CampaignFixRollbackResult(
                source_check=item["source_check"],
                operation=item["operation"],
                target=item["target"],
                status=item["status"],
                detail=item["detail"],
            )
            for item in raw_results
            if isinstance(item, dict)
        )
        report = CampaignFixRollbackExecutionReport(
            campaign_name=report_payload["campaign_name"],
            dry_run=report_payload["dry_run"],
            results=results,
        )
        return CampaignFixRollbackHistoryRecord(
            execution_id=payload["execution_id"],
            campaign_name=payload["campaign_name"],
            executed_at=datetime.fromisoformat(payload["executed_at"]),
            report=report,
        )
