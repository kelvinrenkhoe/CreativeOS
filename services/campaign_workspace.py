"""Read-only operational campaign workspace composition."""

from dataclasses import dataclass
from pathlib import Path

from models.campaign_context import CampaignContext
from services.action_repository import ActionRepository
from services.campaign_asset_readiness import AssetReadinessReport, CampaignAssetReadinessService
from services.campaign_asset_repository import CampaignAssetRepository
from services.campaign_context import CampaignContextService
from services.content_inventory import ContentInventoryRepository
from services.content_inventory_inspection import ContentInventoryInspectionService


@dataclass(frozen=True, slots=True)
class CampaignWorkspaceReport:
    """One deterministic operational view across campaign production state."""

    campaign: CampaignContext
    content_items: int
    actions: int
    completed_actions: int
    blocked_action_ids: tuple[str, ...]
    pending_action_ids: tuple[str, ...]
    asset_readiness: AssetReadinessReport
    content_gap_ids: tuple[str, ...]

    @property
    def open_actions(self) -> int:
        """Return actions not yet completed or cancelled."""
        return len(self.pending_action_ids) + len(self.blocked_action_ids)

    @property
    def attention_ids(self) -> tuple[str, ...]:
        """Return stable identifiers currently requiring operator attention."""
        return tuple(
            dict.fromkeys(
                (
                    *self.blocked_action_ids,
                    *self.content_gap_ids,
                    *self.asset_readiness.missing_location,
                )
            )
        )


class CampaignWorkspaceService:
    """Compose existing campaign services into one side-effect-free workspace view."""

    def __init__(
        self,
        repository_root: Path,
        organization_id: str,
        project_id: str,
        campaign_id: str,
    ) -> None:
        self.campaign_context = CampaignContextService(
            repository_root,
            organization_id,
            project_id,
        )
        self.campaign_id = campaign_id
        self.content = ContentInventoryRepository(
            repository_root,
            organization_id,
            project_id,
            campaign_id,
        )
        self.actions = ActionRepository(
            repository_root,
            organization_id,
            project_id,
            campaign_id,
        )
        self.assets = CampaignAssetRepository(
            repository_root,
            organization_id,
            project_id,
            campaign_id,
        )

    def inspect(self) -> CampaignWorkspaceReport:
        """Return the current campaign operational state without modifying it."""
        campaign = self.campaign_context.load(self.campaign_id)
        content_report = ContentInventoryInspectionService(self.content).inspect()
        actions = self.actions.list()
        assets = self.assets.list()
        asset_readiness = CampaignAssetReadinessService().inspect(assets)

        blocked = tuple(action.action_id for action in actions if action.status == "blocked")
        pending = tuple(
            action.action_id
            for action in actions
            if action.status in ("pending", "in-progress")
        )
        completed = sum(action.status == "completed" for action in actions)
        content_gaps = tuple(
            dict.fromkeys(
                (
                    *content_report.missing_role_ids,
                    *content_report.missing_format_ids,
                    *content_report.missing_channel_ids,
                    *content_report.missing_call_to_action_ids,
                )
            )
        )

        return CampaignWorkspaceReport(
            campaign=campaign,
            content_items=content_report.total_items,
            actions=len(actions),
            completed_actions=completed,
            blocked_action_ids=blocked,
            pending_action_ids=pending,
            asset_readiness=asset_readiness,
            content_gap_ids=content_gaps,
        )
