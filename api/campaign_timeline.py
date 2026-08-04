"""Structured API for deterministic campaign release timelines."""

from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path

import yaml

from core.project import Project
from models.campaign import CampaignManifest
from models.campaign_release_timeline import CampaignReleaseTimelineEvent
from services.campaign import slugify
from services.campaign_release_timeline import CampaignReleaseTimelineService


@dataclass(frozen=True, slots=True)
class CampaignTimelineResult:
    """Structured outcome returned by the campaign timeline API."""

    campaign: str
    release_date: date | None = None
    campaign_type: str = "music-release"
    timeline_events: tuple[CampaignReleaseTimelineEvent, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether the timeline was generated without errors."""
        return not self.errors


class CampaignTimelineAPI:
    """Load campaign data and return deterministic timeline results."""

    def __init__(
        self,
        project: Project,
        service: CampaignReleaseTimelineService | None = None,
    ) -> None:
        self.project = project
        self.service = service or CampaignReleaseTimelineService()

    def timeline(self, campaign_name: str) -> CampaignTimelineResult:
        """Return a structured release timeline for one campaign."""
        campaign_path = self.project.campaigns_path / slugify(campaign_name)
        manifest_path = campaign_path / "campaign.yaml"

        if not campaign_path.is_dir():
            return CampaignTimelineResult(
                campaign=campaign_name,
                errors=(
                    f'Campaign workspace not found for "{campaign_name}". '
                    f'Run: creativeos campaign create "{campaign_name}"',
                ),
            )
        if not manifest_path.is_file():
            return CampaignTimelineResult(
                campaign=campaign_name,
                errors=(f"Campaign manifest not found: {manifest_path}",),
            )

        manifest, error = self._load_manifest(manifest_path)
        if error is not None:
            return CampaignTimelineResult(
                campaign=campaign_name,
                errors=(error,),
            )
        assert manifest is not None

        if not manifest.release_date:
            return CampaignTimelineResult(
                campaign=campaign_name,
                errors=(
                    f'Release date is not configured for "{campaign_name}". '
                    "Add release_date to campaign.yaml using YYYY-MM-DD.",
                ),
            )

        try:
            release_date = date.fromisoformat(manifest.release_date)
        except (TypeError, ValueError):
            return CampaignTimelineResult(
                campaign=campaign_name,
                errors=(f"Invalid release date: {manifest.release_date}; expected YYYY-MM-DD",),
            )

        timeline = self.service.generate(release_date)
        return CampaignTimelineResult(
            campaign=campaign_name,
            release_date=timeline.release_date,
            campaign_type=timeline.campaign_type,
            timeline_events=timeline.events,
        )

    @staticmethod
    def _load_manifest(path: Path) -> tuple[CampaignManifest | None, str | None]:
        """Load one campaign manifest without modifying the filesystem."""
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            return None, f"Invalid campaign manifest: {exc}"

        if not isinstance(loaded, dict):
            return None, "Campaign manifest must contain a mapping"

        allowed_fields = {field.name for field in fields(CampaignManifest)}
        manifest_data = {key: value for key, value in loaded.items() if key in allowed_fields}
        if isinstance(manifest_data.get("release_date"), date):
            manifest_data["release_date"] = manifest_data["release_date"].isoformat()

        try:
            return CampaignManifest(**manifest_data), None
        except (TypeError, ValueError) as exc:
            return None, f"Invalid campaign manifest: {exc}"
