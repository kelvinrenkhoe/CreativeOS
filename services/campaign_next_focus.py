"""Deterministic next-focus recommendation for campaign operations."""

from dataclasses import dataclass

from services.campaign_attention import CampaignAttentionItem, CampaignAttentionService
from services.campaign_workspace import CampaignWorkspaceReport


@dataclass(frozen=True, slots=True)
class CampaignNextFocus:
    """One explainable recommendation for the operator's next campaign focus."""

    item: CampaignAttentionItem | None
    pending_action_ids: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """Return whether the workspace has no current attention item."""
        return self.item is None


class CampaignNextFocusService:
    """Select one next focus from already-prioritised workspace attention."""

    def __init__(self, attention: CampaignAttentionService | None = None) -> None:
        self.attention = attention or CampaignAttentionService()

    def recommend(self, report: CampaignWorkspaceReport) -> CampaignNextFocus:
        """Return the first deterministic priority item plus pending work context."""
        items = self.attention.prioritise(report)
        return CampaignNextFocus(
            item=items[0] if items else None,
            pending_action_ids=report.pending_action_ids,
        )
