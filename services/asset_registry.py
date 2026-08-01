"""Deterministic in-memory registry for creative asset intelligence."""

from dataclasses import dataclass

from models.asset_intelligence import (
    AssetIntelligenceError,
    AssetStatus,
    AssetType,
    CreativeAsset,
)


@dataclass(frozen=True, slots=True)
class AssetSimilarity:
    """A deterministic similarity result between two assets."""

    asset_id: str
    compared_asset_id: str
    score: float
    exact_match: bool


class AssetIntelligenceRegistry:
    """Record, query, and compare creative asset metadata without side effects."""

    def __init__(self, assets: tuple[CreativeAsset, ...] = ()) -> None:
        self._assets: list[CreativeAsset] = []
        self._by_id: dict[str, CreativeAsset] = {}
        for asset in assets:
            self.register(asset)

    @property
    def assets(self) -> tuple[CreativeAsset, ...]:
        """Return assets in stable registration order."""
        return tuple(self._assets)

    def register(self, asset: CreativeAsset) -> None:
        """Register one immutable asset record."""
        if not isinstance(asset, CreativeAsset):
            raise AssetIntelligenceError("asset must be a CreativeAsset")
        if asset.asset_id in self._by_id:
            raise AssetIntelligenceError(f"duplicate asset_id: {asset.asset_id}")
        self._assets.append(asset)
        self._by_id[asset.asset_id] = asset

    def get(self, asset_id: str) -> CreativeAsset:
        """Return one asset by ID or fail clearly."""
        try:
            return self._by_id[asset_id]
        except KeyError as exc:
            raise AssetIntelligenceError(f"unknown asset_id: {asset_id}") from exc

    def query(
        self,
        *,
        campaign_id: str | None = None,
        asset_type: AssetType | None = None,
        platform: str | None = None,
        status: AssetStatus | None = None,
        used: bool | None = None,
    ) -> tuple[CreativeAsset, ...]:
        """Filter assets while preserving registration order."""
        platform_key = platform.strip().casefold() if platform is not None else None
        return tuple(
            asset
            for asset in self._assets
            if (campaign_id is None or asset.campaign_id == campaign_id)
            and (asset_type is None or asset.asset_type is asset_type)
            and (platform_key is None or asset.platform.casefold() == platform_key)
            and (status is None or asset.status is status)
            and (used is None or bool(asset.usages) is used)
        )

    def similarity(self, asset_id: str, compared_asset_id: str) -> AssetSimilarity:
        """Compare two registered assets using Jaccard token overlap."""
        return self._compare(self.get(asset_id), self.get(compared_asset_id))

    def similar_to(
        self,
        asset: CreativeAsset,
        *,
        threshold: float = 0.6,
        campaign_id: str | None = None,
    ) -> tuple[AssetSimilarity, ...]:
        """Return existing assets meeting a deterministic similarity threshold."""
        if not 0 <= threshold <= 1:
            raise AssetIntelligenceError("threshold must be between 0 and 1")
        results: list[AssetSimilarity] = []
        for existing in self._assets:
            if campaign_id is not None and existing.campaign_id != campaign_id:
                continue
            result = self._compare(asset, existing)
            if result.score >= threshold:
                results.append(result)
        return tuple(results)

    def excluded_asset_ids(
        self,
        asset: CreativeAsset,
        *,
        threshold: float = 0.6,
        campaign_id: str | None = None,
    ) -> tuple[str, ...]:
        """Return IDs a generator should avoid reusing for a new direction."""
        return tuple(
            result.compared_asset_id
            for result in self.similar_to(
                asset,
                threshold=threshold,
                campaign_id=campaign_id,
            )
        )

    @staticmethod
    def _compare(asset: CreativeAsset, compared: CreativeAsset) -> AssetSimilarity:
        left = set(asset.fingerprint_tokens)
        right = set(compared.fingerprint_tokens)
        union = left.union(right)
        score = 1.0 if not union else len(left.intersection(right)) / len(union)
        return AssetSimilarity(
            asset_id=asset.asset_id,
            compared_asset_id=compared.asset_id,
            score=score,
            exact_match=asset.fingerprint == compared.fingerprint,
        )
