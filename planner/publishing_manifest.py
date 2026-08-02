"""Build deterministic publishing manifests without posting or scheduling."""

import json

from models.campaign_package import CampaignPackage, PackageAsset, PackageMediaType
from models.publishing import PublishingError, PublishingManifest, PublishingSlot


class PublishingManifestPlanner:
    """Validate package-backed publishing slots and render a stable manifest asset."""

    def plan(
        self,
        package: CampaignPackage,
        slots: tuple[PublishingSlot, ...],
        *,
        timezone: str,
    ) -> PublishingManifest:
        package_paths = set(package.manifest.asset_paths)
        ordered = tuple(sorted(slots, key=lambda slot: (slot.day, slot.time, slot.slot_id)))
        for slot in ordered:
            required = {slot.primary_asset_path, *slot.supporting_asset_paths}
            missing = sorted(required - package_paths)
            if missing:
                missing_assets = ", ".join(missing)
                raise PublishingError(
                    f"publishing slot {slot.slot_id} references missing assets: "
                    f"{missing_assets}"
                )
        return PublishingManifest(
            manifest_id=f"{package.package_id}-publishing",
            campaign_id=package.metadata.campaign_id,
            campaign_week=package.metadata.campaign_week,
            timezone=timezone,
            slots=ordered,
        )

    def package_asset(self, manifest: PublishingManifest) -> PackageAsset:
        return PackageAsset(
            path="publishing/publishing_manifest.json",
            media_type=PackageMediaType.JSON,
            content=json.dumps(
                {
                    "campaign_id": manifest.campaign_id,
                    "campaign_week": manifest.campaign_week,
                    "manifest_id": manifest.manifest_id,
                    "slots": [
                        {
                            "approval_status": slot.approval_status.value,
                            "content_format": slot.content_format.value,
                            "day": slot.day,
                            "dependency_slot_ids": slot.dependency_slot_ids,
                            "platform": slot.platform.value,
                            "primary_asset_path": slot.primary_asset_path,
                            "slot_id": slot.slot_id,
                            "supporting_asset_paths": slot.supporting_asset_paths,
                            "time": slot.time,
                        }
                        for slot in manifest.slots
                    ],
                    "timezone": manifest.timezone,
                },
                indent=2,
                sort_keys=True,
            ),
        )
