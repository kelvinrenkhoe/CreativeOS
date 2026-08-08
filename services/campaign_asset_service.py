"""Deterministic lifecycle operations for campaign-scoped assets."""

from dataclasses import replace

from models.campaign_asset import CampaignAsset, CampaignAssetError
from services.campaign_asset_repository import (
    CampaignAssetRepository,
    CampaignAssetRepositoryError,
)

_ALLOWED_TRANSITIONS = {
    "planned": ("draft",),
    "draft": ("review",),
    "review": ("draft", "approved"),
    "approved": ("review", "published"),
    "published": (),
}


class CampaignAssetServiceError(ValueError):
    """Raised when an asset lifecycle operation is invalid or unsafe."""


class CampaignAssetService:
    """Apply deterministic asset updates within one campaign repository."""

    def __init__(self, repository: CampaignAssetRepository) -> None:
        self.repository = repository

    def transition(self, asset_id: str, target_status: str) -> CampaignAsset:
        """Move one asset through an allowed lifecycle transition."""
        asset = self._load(asset_id)
        normalized = target_status.strip().casefold()
        allowed = _ALLOWED_TRANSITIONS[asset.status]
        if normalized not in allowed:
            raise CampaignAssetServiceError(
                f"cannot transition asset from {asset.status!r} to {normalized!r}"
            )
        return self._replace(asset, status=normalized)

    def link_content(self, asset_id: str, content_id: str | None) -> CampaignAsset:
        """Attach or clear the content item associated with an asset."""
        asset = self._load(asset_id)
        return self._replace(asset, content_id=content_id)

    def link_action(self, asset_id: str, action_id: str | None) -> CampaignAsset:
        """Attach or clear the execution action associated with an asset."""
        asset = self._load(asset_id)
        return self._replace(asset, action_id=action_id)

    def set_location(self, asset_id: str, location: str | None) -> CampaignAsset:
        """Attach or clear the physical/digital artifact location."""
        asset = self._load(asset_id)
        return self._replace(asset, location=location)

    def _replace(self, asset: CampaignAsset, **changes: object) -> CampaignAsset:
        try:
            updated = replace(asset, **changes)
            self.repository.replace(updated)
            return updated
        except (CampaignAssetError, CampaignAssetRepositoryError) as exc:
            raise CampaignAssetServiceError(str(exc)) from exc

    def _load(self, asset_id: str) -> CampaignAsset:
        try:
            return self.repository.load(asset_id)
        except CampaignAssetRepositoryError as exc:
            raise CampaignAssetServiceError(str(exc)) from exc
