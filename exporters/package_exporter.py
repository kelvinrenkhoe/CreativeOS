"""Build deterministic in-memory weekly creative campaign packages."""

import json
import re

from models.campaign_package import (
    CampaignPackage,
    PackageAsset,
    PackageError,
    PackageManifest,
    PackageMediaType,
    PackageMetadata,
)
from models.creative_brief import CreativeBrief

_REQUIRED_PATHS = frozenset(
    {
        "strategy/creative_brief.md",
        "strategy/storyboard.md",
    }
)


class PackageExporter:
    """Bundle campaign outputs without writing to disk."""

    def export(
        self,
        brief: CreativeBrief,
        campaign_week: int,
        assets: tuple[PackageAsset, ...],
        *,
        creativeos_version: str,
        generated_at: str,
        schema_version: int = 1,
    ) -> CampaignPackage:
        if campaign_week < 1:
            raise PackageError("campaign_week must be positive")

        supplied_paths = {asset.path for asset in assets}
        missing = sorted(_REQUIRED_PATHS - supplied_paths)
        if missing:
            raise PackageError(f"missing required assets: {', '.join(missing)}")
        if len(supplied_paths) != len(assets):
            raise PackageError("asset paths must be unique")

        package_id = f"{brief.campaign_id}-week-{campaign_week:02d}"
        metadata = PackageMetadata(
            creativeos_version=creativeos_version,
            schema_version=schema_version,
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=campaign_week,
            generated_at=generated_at,
        )

        generated_paths = ("README.md", "manifest.json", "metadata.json")
        all_paths = tuple(sorted((*supplied_paths, *generated_paths)))
        manifest = PackageManifest(
            package_id=package_id,
            campaign_id=brief.campaign_id,
            campaign_week=campaign_week,
            asset_paths=all_paths,
        )
        generated_assets = (
            PackageAsset(
                path="README.md",
                media_type=PackageMediaType.MARKDOWN,
                content=self._readme(brief, campaign_week, all_paths),
            ),
            PackageAsset(
                path="manifest.json",
                media_type=PackageMediaType.JSON,
                content=self._manifest_json(manifest),
            ),
            PackageAsset(
                path="metadata.json",
                media_type=PackageMediaType.JSON,
                content=self._metadata_json(metadata),
            ),
        )
        ordered_assets = tuple(sorted((*assets, *generated_assets), key=lambda asset: asset.path))
        root_path = f"{_slugify(brief.campaign_name)}/Week-{campaign_week:02d}"
        return CampaignPackage(
            package_id=package_id,
            root_path=root_path,
            metadata=metadata,
            manifest=manifest,
            assets=ordered_assets,
        )

    @staticmethod
    def _readme(brief: CreativeBrief, campaign_week: int, paths: tuple[str, ...]) -> str:
        assets = "\n".join(f"- `{path}`" for path in paths)
        return "\n".join(
            (
                f"# {brief.campaign_name} — Week {campaign_week}",
                "",
                f"Artist: {brief.artist}",
                f"Objective: {brief.objective}",
                f"Audience: {brief.audience}",
                f"Platforms: {', '.join(brief.platforms)}",
                "",
                "## Package Assets",
                assets,
                "",
                "## Next Recommended Action",
                brief.next_reason or "Review and approve the weekly creative package.",
            )
        )

    @staticmethod
    def _manifest_json(manifest: PackageManifest) -> str:
        return json.dumps(
            {
                "asset_paths": manifest.asset_paths,
                "campaign_id": manifest.campaign_id,
                "campaign_week": manifest.campaign_week,
                "package_id": manifest.package_id,
            },
            indent=2,
            sort_keys=True,
        )

    @staticmethod
    def _metadata_json(metadata: PackageMetadata) -> str:
        return json.dumps(
            {
                "campaign_id": metadata.campaign_id,
                "campaign_name": metadata.campaign_name,
                "campaign_week": metadata.campaign_week,
                "creativeos_version": metadata.creativeos_version,
                "generated_at": metadata.generated_at,
                "schema_version": metadata.schema_version,
            },
            indent=2,
            sort_keys=True,
        )


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
