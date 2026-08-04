"""Structured API for deterministic campaign readiness analytics."""

from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path

import yaml

from core.project import Project
from models.campaign import CampaignManifest
from services.campaign import slugify


@dataclass(frozen=True, slots=True)
class CampaignAnalyticsResult:
    """Structured readiness summary for one campaign."""

    campaign: str
    readiness_score: int = 0
    health: str = "needs-attention"
    release_date: date | None = None
    days_to_release: int | None = None
    configured_checks: tuple[str, ...] = ()
    missing_checks: tuple[str, ...] = ()
    platform_count: int = 0
    goal_count: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether analytics were calculated without errors."""
        return not self.errors


class CampaignAnalyticsAPI:
    """Calculate deterministic readiness analytics from campaign manifests."""

    _CHECKS = (
        "release_date",
        "spotify",
        "smart_link",
        "hashtags",
        "platforms",
        "goals",
    )

    def __init__(self, project: Project) -> None:
        self.project = project

    def summary(
        self,
        campaign_name: str,
        *,
        today: date | None = None,
    ) -> CampaignAnalyticsResult:
        """Return a structured readiness summary for one campaign."""
        campaign_path = self.project.campaigns_path / slugify(campaign_name)
        manifest_path = campaign_path / "campaign.yaml"

        if not campaign_path.is_dir():
            return CampaignAnalyticsResult(
                campaign=campaign_name,
                errors=(
                    f'Campaign workspace not found for "{campaign_name}". '
                    f'Run: creativeos campaign create "{campaign_name}"',
                ),
            )
        if not manifest_path.is_file():
            return CampaignAnalyticsResult(
                campaign=campaign_name,
                errors=(f"Campaign manifest not found: {manifest_path}",),
            )

        manifest, error = self._load_manifest(manifest_path)
        if error is not None:
            return CampaignAnalyticsResult(campaign=campaign_name, errors=(error,))
        assert manifest is not None

        configured = tuple(
            check for check in self._CHECKS if self._is_configured(manifest, check)
        )
        missing = tuple(check for check in self._CHECKS if check not in configured)
        score = round(len(configured) / len(self._CHECKS) * 100)

        release_date, release_error = self._parse_release_date(manifest.release_date)
        warnings: list[str] = []
        if release_error is not None:
            warnings.append(release_error)

        reference_date = today or date.today()
        days_to_release = (
            (release_date - reference_date).days if release_date is not None else None
        )
        if days_to_release is not None and days_to_release < 0:
            warnings.append("Campaign release date is in the past")

        return CampaignAnalyticsResult(
            campaign=campaign_name,
            readiness_score=score,
            health=self._health(score),
            release_date=release_date,
            days_to_release=days_to_release,
            configured_checks=configured,
            missing_checks=missing,
            platform_count=len(manifest.platforms),
            goal_count=len(manifest.goals),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _health(score: int) -> str:
        if score == 100:
            return "ready"
        if score >= 70:
            return "on-track"
        return "needs-attention"

    @staticmethod
    def _is_configured(manifest: CampaignManifest, check: str) -> bool:
        value = getattr(manifest, check)
        if isinstance(value, str):
            return bool(value.strip())
        return bool(value)

    @staticmethod
    def _parse_release_date(value: str | None) -> tuple[date | None, str | None]:
        if not value:
            return None, None
        try:
            return date.fromisoformat(value), None
        except (TypeError, ValueError):
            return None, f"Invalid release date: {value}; expected YYYY-MM-DD"

    @staticmethod
    def _load_manifest(path: Path) -> tuple[CampaignManifest | None, str | None]:
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
