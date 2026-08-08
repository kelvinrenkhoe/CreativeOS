"""Safe campaign-start planning for organization project campaigns."""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yaml

from models.campaign_context import CampaignContext
from services.campaign_context import CAMPAIGN_FILENAME, CampaignContextService


class CampaignStartError(ValueError):
    """Reject invalid or unsafe campaign-start requests."""


@dataclass(frozen=True, slots=True)
class CampaignStartPlan:
    """Previewable campaign context prepared for creation."""

    campaign: CampaignContext
    release_date: date
    destination: Path


class CampaignStartService:
    """Prepare and safely create a music-release campaign context."""

    def __init__(
        self,
        repository_root: Path,
        organization_id: str,
        project_id: str,
    ) -> None:
        self.context_service = CampaignContextService(
            repository_root,
            organization_id,
            project_id,
        )

    def plan(
        self,
        campaign_id: str,
        name: str,
        release_date: date,
        *,
        objective: str,
        channels: tuple[str, ...],
    ) -> CampaignStartPlan:
        """Return a deterministic music-release campaign plan without writing files."""
        if not channels:
            raise CampaignStartError("at least one campaign channel is required")

        campaign = CampaignContext(
            campaign_id=campaign_id,
            name=name,
            campaign_type="music-release",
            status="draft",
            objective=objective,
            start_date=release_date - timedelta(days=21),
            end_date=release_date + timedelta(days=7),
            channels=channels,
            milestones=(
                ("campaign_start", release_date - timedelta(days=21)),
                ("content_freeze", release_date - timedelta(days=7)),
                ("launch", release_date),
                ("performance_review", release_date + timedelta(days=7)),
            ),
        )
        destination = self.context_service.campaigns_root / campaign.campaign_id
        if destination.exists():
            raise CampaignStartError(f"campaign already exists: {campaign.campaign_id}")

        return CampaignStartPlan(
            campaign=campaign,
            release_date=release_date,
            destination=destination,
        )

    def apply(self, plan: CampaignStartPlan) -> CampaignContext:
        """Persist one previously prepared campaign plan."""
        destination = plan.destination.resolve()
        campaigns_root = self.context_service.campaigns_root.resolve()
        if destination.parent != campaigns_root:
            raise CampaignStartError("campaign destination escaped the project campaigns directory")
        if destination.exists():
            raise CampaignStartError(f"campaign already exists: {plan.campaign.campaign_id}")

        destination.mkdir(parents=True)
        config_path = destination / CAMPAIGN_FILENAME
        try:
            config_path.write_text(
                yaml.safe_dump(self._to_dict(plan.campaign), sort_keys=False),
                encoding="utf-8",
            )
        except OSError:
            if config_path.exists():
                config_path.unlink()
            try:
                destination.rmdir()
            except OSError:
                pass
            raise

        return self.context_service.load(plan.campaign.campaign_id)

    @staticmethod
    def _to_dict(campaign: CampaignContext) -> dict[str, object]:
        return {
            "id": campaign.campaign_id,
            "name": campaign.name,
            "type": campaign.campaign_type,
            "status": campaign.status,
            "objective": campaign.objective,
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "channels": list(campaign.channels),
            "milestones": dict(campaign.milestones),
        }
