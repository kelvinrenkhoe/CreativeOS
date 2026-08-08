"""Read-only campaign asset production readiness reporting."""

from dataclasses import dataclass

from models.campaign_asset import CampaignAsset


@dataclass(frozen=True, slots=True)
class AssetReadinessReport:
    """Deterministic summary of campaign production readiness."""

    total_assets: int
    planned: int
    draft: int
    review: int
    approved: int
    published: int
    unlinked_content: tuple[str, ...]
    missing_location: tuple[str, ...]

    @property
    def ready_assets(self) -> int:
        """Return assets ready for or already through distribution."""
        return self.approved + self.published

    @property
    def ready_ratio(self) -> float:
        """Return the stable readiness ratio for the campaign asset set."""
        return 1.0 if self.total_assets == 0 else self.ready_assets / self.total_assets


class CampaignAssetReadinessService:
    """Inspect immutable asset records without changing campaign state."""

    def inspect(self, assets: tuple[CampaignAsset, ...]) -> AssetReadinessReport:
        """Return status counts and production-linkage gaps."""
        counts = {status: 0 for status in ("planned", "draft", "review", "approved", "published")}
        unlinked_content: list[str] = []
        missing_location: list[str] = []

        for asset in assets:
            counts[asset.status] += 1
            if asset.content_id is None:
                unlinked_content.append(asset.asset_id)
            if asset.status in ("approved", "published") and asset.location is None:
                missing_location.append(asset.asset_id)

        return AssetReadinessReport(
            total_assets=len(assets),
            planned=counts["planned"],
            draft=counts["draft"],
            review=counts["review"],
            approved=counts["approved"],
            published=counts["published"],
            unlinked_content=tuple(unlinked_content),
            missing_location=tuple(missing_location),
        )
