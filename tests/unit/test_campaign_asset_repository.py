from pathlib import Path

import pytest

from models.campaign_asset import CampaignAsset
from services.campaign_asset_repository import (
    CampaignAssetRepository,
    CampaignAssetRepositoryError,
)


def repository(tmp_path: Path) -> CampaignAssetRepository:
    return CampaignAssetRepository(tmp_path, "acme", "product-launch", "spring-launch")


def test_asset_repository_saves_and_lists_campaign_assets(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    video = CampaignAsset(
        "launch-video",
        "Launch video",
        "video",
        content_id="launch-announcement",
    )
    artwork = CampaignAsset("launch-artwork", "Launch artwork", "image")

    repo.save(video)
    repo.save(artwork)

    assert [asset.asset_id for asset in repo.list()] == ["launch-artwork", "launch-video"]
    assert repo.load("launch-video") == video


def test_asset_repository_refuses_duplicate_records(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    asset = CampaignAsset("launch-video", "Launch video", "video")
    repo.save(asset)

    with pytest.raises(CampaignAssetRepositoryError, match="already exists"):
        repo.save(asset)


def test_asset_repository_is_campaign_scoped(tmp_path: Path) -> None:
    first = repository(tmp_path)
    second = CampaignAssetRepository(tmp_path, "acme", "product-launch", "autumn-launch")
    first.save(CampaignAsset("launch-video", "Launch video", "video"))

    assert second.list() == ()


def test_asset_repository_rejects_unsafe_lookup_id(tmp_path: Path) -> None:
    repo = repository(tmp_path)

    with pytest.raises(CampaignAssetRepositoryError, match="path-safe identifier"):
        repo.load("../outside")
