"""Read-only campaign readiness checks for CreativeOS."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from core.project import Project
from models.campaign import CampaignManifest
from models.doctor import DoctorCheck, DoctorReport
from orchestrator.models import PipelineError
from orchestrator.presets import CampaignRuntimePresetRegistry
from services.campaign import slugify


class CampaignDoctorService:
    """Diagnose whether an existing campaign is ready for execution."""

    def __init__(
        self,
        project: Project,
        preset_registry: CampaignRuntimePresetRegistry,
    ) -> None:
        self.project = project
        self.preset_registry = preset_registry

    def diagnose(
        self,
        campaign_name: str,
        *,
        preset_name: str = "music-release",
        context: Mapping[str, Any] | None = None,
    ) -> DoctorReport:
        """Return a deterministic, read-only readiness report."""
        campaign_path = self.project.campaigns_path / slugify(campaign_name)
        manifest_path = campaign_path / "campaign.yaml"

        checks: list[DoctorCheck] = [
            DoctorCheck(
                category="Campaign",
                name="Campaign workspace",
                passed=campaign_path.is_dir(),
                detail=str(campaign_path),
            ),
            DoctorCheck(
                category="Campaign",
                name="Campaign manifest",
                passed=manifest_path.is_file(),
                detail=str(manifest_path),
            ),
        ]

        manifest = self._load_manifest(manifest_path)

        if manifest is None:
            checks.append(
                DoctorCheck(
                    category="Campaign",
                    name="Manifest configuration",
                    passed=False,
                    detail="campaign.yaml is missing or invalid",
                )
            )
        else:
            checks.extend(self._manifest_checks(manifest))
            checks.extend(self._asset_checks(campaign_path))

        checks.extend(
            self._preset_checks(
                preset_name=preset_name,
                context=context or {},
            )
        )

        return DoctorReport(checks=tuple(checks))

    @staticmethod
    def _load_manifest(path: Path) -> CampaignManifest | None:
        """Load a campaign manifest without modifying the filesystem."""
        if not path.is_file():
            return None

        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            return None

        if not isinstance(loaded, dict):
            return None

        allowed_fields = {field.name for field in fields(CampaignManifest)}
        manifest_data = {key: value for key, value in loaded.items() if key in allowed_fields}

        try:
            return CampaignManifest(**manifest_data)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _manifest_checks(
        cls,
        manifest: CampaignManifest,
    ) -> tuple[DoctorCheck, ...]:
        """Validate required and optional campaign manifest fields."""
        release_date_valid, release_date_detail = cls._validate_release_date(manifest.release_date)

        return (
            DoctorCheck(
                category="Campaign",
                name="Campaign name",
                passed=bool(manifest.name.strip()),
                detail=manifest.name or "Missing campaign name",
            ),
            DoctorCheck(
                category="Campaign",
                name="Artist",
                passed=bool(manifest.artist.strip()),
                detail=manifest.artist or "Missing artist name",
            ),
            DoctorCheck(
                category="Campaign",
                name="Release date",
                passed=release_date_valid,
                detail=release_date_detail,
            ),
            DoctorCheck(
                category="Strategy",
                name="Platforms",
                passed=bool(manifest.platforms),
                detail=", ".join(manifest.platforms) or "No platforms configured",
                required=False,
            ),
            DoctorCheck(
                category="Strategy",
                name="Campaign goals",
                passed=bool(manifest.goals),
                detail=(
                    f"{len(manifest.goals)} goals configured"
                    if manifest.goals
                    else "No campaign goals configured"
                ),
                required=False,
            ),
            DoctorCheck(
                category="Distribution",
                name="Streaming link",
                passed=bool(manifest.spotify or manifest.smart_link),
                detail=manifest.smart_link or manifest.spotify or "No streaming link",
                required=False,
            ),
        )

    @staticmethod
    def _validate_release_date(value: str | None) -> tuple[bool, str]:
        """Validate an ISO-8601 campaign release date."""
        if not value:
            return False, "Release date is not configured"

        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return False, f"Invalid release date: {value}; expected YYYY-MM-DD"

        return True, parsed.isoformat()

    @staticmethod
    def _asset_checks(campaign_path: Path) -> tuple[DoctorCheck, ...]:
        """Check optional campaign files and asset areas."""
        return (
            CampaignDoctorService._optional_file_check(
                campaign_path / "README.md",
                category="Campaign",
                name="Campaign README",
            ),
            CampaignDoctorService._optional_populated_directory_check(
                campaign_path / "assets" / "artwork",
                category="Assets",
                name="Artwork",
            ),
            CampaignDoctorService._optional_populated_directory_check(
                campaign_path / "assets" / "videos",
                category="Assets",
                name="Video assets",
            ),
            CampaignDoctorService._optional_nonempty_file_check(
                campaign_path / "schedule" / "content-calendar.md",
                category="Planning",
                name="Content calendar",
            ),
            CampaignDoctorService._optional_nonempty_file_check(
                campaign_path / "press" / "press-release.md",
                category="Promotion",
                name="Press release",
            ),
            CampaignDoctorService._optional_nonempty_file_check(
                campaign_path / "radio" / "stations.csv",
                category="Promotion",
                name="Radio outreach",
            ),
        )

    def _preset_checks(
        self,
        *,
        preset_name: str,
        context: Mapping[str, Any],
    ) -> tuple[DoctorCheck, ...]:
        """Validate preset availability and required runtime context."""
        try:
            preset = self.preset_registry.get(preset_name)
        except PipelineError as exc:
            return (
                DoctorCheck(
                    category="Runtime",
                    name="Runtime preset",
                    passed=False,
                    detail=str(exc),
                ),
            )

        checks = [
            DoctorCheck(
                category="Runtime",
                name="Runtime preset",
                passed=True,
                detail=preset.name,
            )
        ]

        checks.extend(
            DoctorCheck(
                category="Runtime",
                name=f"Context: {key}",
                passed=key in context and context[key] is not None,
                detail=(
                    "Available"
                    if key in context and context[key] is not None
                    else f"Missing required context key: {key}"
                ),
            )
            for key in preset.required_context_keys
        )

        return tuple(checks)

    @staticmethod
    def _optional_file_check(
        path: Path,
        *,
        category: str,
        name: str,
    ) -> DoctorCheck:
        return DoctorCheck(
            category=category,
            name=name,
            passed=path.is_file(),
            detail=str(path),
            required=False,
        )

    @staticmethod
    def _optional_nonempty_file_check(
        path: Path,
        *,
        category: str,
        name: str,
    ) -> DoctorCheck:
        passed = path.is_file() and path.stat().st_size > 0
        return DoctorCheck(
            category=category,
            name=name,
            passed=passed,
            detail=str(path),
            required=False,
        )

    @staticmethod
    def _optional_populated_directory_check(
        path: Path,
        *,
        category: str,
        name: str,
    ) -> DoctorCheck:
        passed = path.is_dir() and any(item.is_file() for item in path.iterdir())
        return DoctorCheck(
            category=category,
            name=name,
            passed=passed,
            detail=str(path),
            required=False,
        )
