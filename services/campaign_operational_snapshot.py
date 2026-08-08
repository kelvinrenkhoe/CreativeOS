"""Stable machine-readable snapshot of campaign operational state."""

from dataclasses import dataclass

from .campaign_attention import CampaignAttentionService
from .campaign_next_focus import CampaignNextFocusService
from .campaign_workspace import CampaignWorkspaceReport


SNAPSHOT_SCHEMA_VERSION = "1"


@dataclass(frozen=True, slots=True)
class CampaignOperationalSnapshot:
    """Serializable operational contract for API, reporting, and integrations."""

    schema_version: str
    campaign: dict[str, object]
    execution: dict[str, object]
    assets: dict[str, object]
    attention: tuple[dict[str, object], ...]
    next_focus: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation with a stable top-level shape."""
        return {
            "schema_version": self.schema_version,
            "campaign": self.campaign,
            "execution": self.execution,
            "assets": self.assets,
            "attention": self.attention,
            "next_focus": self.next_focus,
        }


class CampaignOperationalSnapshotService:
    """Compose existing read models into one versioned machine-readable contract."""

    def __init__(
        self,
        attention: CampaignAttentionService | None = None,
        next_focus: CampaignNextFocusService | None = None,
    ) -> None:
        self.attention = attention or CampaignAttentionService()
        self.next_focus = next_focus or CampaignNextFocusService(self.attention)

    def build(self, report: CampaignWorkspaceReport) -> CampaignOperationalSnapshot:
        """Build a side-effect-free snapshot from one workspace report."""
        attention = self.attention.prioritise(report)
        recommendation = self.next_focus.recommend(report)
        focus = recommendation.item

        return CampaignOperationalSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            campaign={
                "id": report.campaign.campaign_id,
                "name": report.campaign.name,
                "type": report.campaign.campaign_type,
                "status": report.campaign.status,
                "content_items": report.content_items,
            },
            execution={
                "actions": report.actions,
                "completed_actions": report.completed_actions,
                "open_actions": report.open_actions,
                "blocked_action_ids": list(report.blocked_action_ids),
                "pending_action_ids": list(report.pending_action_ids),
            },
            assets={
                "total": report.asset_readiness.total_assets,
                "ready": report.asset_readiness.ready_assets,
                "ready_ratio": report.asset_readiness.ready_ratio,
                "missing_location_ids": list(report.asset_readiness.missing_location),
                "unlinked_content_ids": list(report.asset_readiness.unlinked_content),
            },
            attention=tuple(
                {
                    "priority": item.priority,
                    "type": item.kind,
                    "id": item.item_id,
                    "reason": item.reason,
                }
                for item in attention
            ),
            next_focus=(
                None
                if focus is None
                else {
                    "priority": focus.priority,
                    "type": focus.kind,
                    "id": focus.item_id,
                    "reason": focus.reason,
                }
            ),
        )
