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


@dataclass(frozen=True, slots=True)
class CampaignTimelineStatusResult:
    """Structured lifecycle status derived from a campaign timeline."""

    campaign: str
    today: date
    campaign_start: date | None = None
    campaign_end: date | None = None
    days_elapsed: int = 0
    days_remaining: int = 0
    duration_days: int = 0
    percent_complete: int = 0
    current_phase: str = "Planning"
    current_milestone: str | None = None
    next_milestone: str | None = None
    overdue_milestones: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether lifecycle status was calculated without errors."""
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
        manifest, error = self._campaign_manifest(campaign_name)
        if error is not None:
            return CampaignTimelineResult(campaign=campaign_name, errors=(error,))
        assert manifest is not None

        release_date, error = self._release_date(campaign_name, manifest)
        if error is not None:
            return CampaignTimelineResult(campaign=campaign_name, errors=(error,))
        assert release_date is not None

        timeline = self.service.generate(release_date)
        return CampaignTimelineResult(
            campaign=campaign_name,
            release_date=timeline.release_date,
            campaign_type=timeline.campaign_type,
            timeline_events=timeline.events,
        )

    def status(
        self,
        campaign_name: str,
        *,
        today: date | None = None,
    ) -> CampaignTimelineStatusResult:
        """Return deterministic campaign lifecycle status for one date."""
        reference_date = today or date.today()
        timeline_result = self.timeline(campaign_name)
        if not timeline_result.successful:
            return CampaignTimelineStatusResult(
                campaign=campaign_name,
                today=reference_date,
                errors=timeline_result.errors,
            )

        events = timeline_result.timeline_events
        if not events:
            return CampaignTimelineStatusResult(
                campaign=campaign_name,
                today=reference_date,
                errors=("Campaign timeline contains no milestones",),
            )

        campaign_start = events[0].date
        campaign_end = events[-1].date
        duration_days = (campaign_end - campaign_start).days + 1
        elapsed = min(max((reference_date - campaign_start).days + 1, 0), duration_days)
        remaining = max((campaign_end - reference_date).days, 0)
        percent_complete = round(elapsed / duration_days * 100)

        completed_events = tuple(event for event in events if event.date <= reference_date)
        upcoming_events = tuple(event for event in events if event.date > reference_date)
        current_milestone = completed_events[-1].title if completed_events else None
        next_milestone = upcoming_events[0].title if upcoming_events else None

        return CampaignTimelineStatusResult(
            campaign=campaign_name,
            today=reference_date,
            campaign_start=campaign_start,
            campaign_end=campaign_end,
            days_elapsed=elapsed,
            days_remaining=remaining,
            duration_days=duration_days,
            percent_complete=percent_complete,
            current_phase=self._phase(reference_date, events),
            current_milestone=current_milestone,
            next_milestone=next_milestone,
            overdue_milestones=len(tuple(event for event in events if event.date < reference_date)),
            warnings=(
                "Milestone completion is not tracked; "
                "overdue_milestones counts elapsed milestones.",
            ),
        )

    def _campaign_manifest(
        self,
        campaign_name: str,
    ) -> tuple[CampaignManifest | None, str | None]:
        campaign_path = self.project.campaigns_path / slugify(campaign_name)
        manifest_path = campaign_path / "campaign.yaml"

        if not campaign_path.is_dir():
            return None, (
                f'Campaign workspace not found for "{campaign_name}". '
                f'Run: creativeos campaign create "{campaign_name}"'
            )
        if not manifest_path.is_file():
            return None, f"Campaign manifest not found: {manifest_path}"
        return self._load_manifest(manifest_path)

    @staticmethod
    def _release_date(
        campaign_name: str,
        manifest: CampaignManifest,
    ) -> tuple[date | None, str | None]:
        if not manifest.release_date:
            return None, (
                f'Release date is not configured for "{campaign_name}". '
                "Add release_date to campaign.yaml using YYYY-MM-DD."
            )
        try:
            return date.fromisoformat(manifest.release_date), None
        except (TypeError, ValueError):
            return None, (f"Invalid release date: {manifest.release_date}; expected YYYY-MM-DD")

    @staticmethod
    def _phase(
        today: date,
        events: tuple[CampaignReleaseTimelineEvent, ...],
    ) -> str:
        start = events[0].date
        end = events[-1].date
        release = next(event.date for event in events if event.day_offset == 0)
        offset = (today - release).days

        if today < start:
            return "Planning"
        if today > end:
            return "Completed"
        if offset <= -15:
            return "Pre-save"
        if offset <= -2:
            return "Promotion"
        if offset <= 1:
            return "Release Week"
        return "Post Release"

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
