"""Persistent campaign rollback history models."""

from dataclasses import dataclass
from datetime import UTC, datetime

from models.campaign_fix_rollback_execution import CampaignFixRollbackExecutionReport


@dataclass(frozen=True)
class CampaignFixRollbackHistoryRecord:
    """Immutable record of one completed rollback execution."""

    execution_id: str
    campaign_name: str
    executed_at: datetime
    report: CampaignFixRollbackExecutionReport

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise ValueError("execution_id must not be empty")
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")
        if self.executed_at.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware")
        if self.report.campaign_name != self.campaign_name:
            raise ValueError("report campaign_name must match history record")

    @classmethod
    def from_report(
        cls,
        report: CampaignFixRollbackExecutionReport,
        *,
        executed_at: datetime | None = None,
    ) -> "CampaignFixRollbackHistoryRecord":
        """Build a deterministic timestamp-based history record."""
        timestamp = (executed_at or datetime.now(UTC)).astimezone(UTC)
        execution_id = timestamp.strftime("rb-%Y%m%dT%H%M%S%fZ")
        return cls(
            execution_id=execution_id,
            campaign_name=report.campaign_name,
            executed_at=timestamp,
            report=report,
        )
