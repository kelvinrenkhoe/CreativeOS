import pytest

from models.campaign_asset import CampaignAsset, CampaignAssetError


def test_campaign_asset_normalizes_operational_metadata() -> None:
    asset = CampaignAsset(
        asset_id="Launch Video",
        title="Launch performance video",
        asset_type="Short Video",
        status="Review",
        content_id="Performance Clip",
        channel="Instagram Reels",
        location="exports/launch-video.mp4",
        action_id="Publish Launch",
    )

    assert asset.asset_id == "launch-video"
    assert asset.asset_type == "short-video"
    assert asset.status == "review"
    assert asset.content_id == "performance-clip"
    assert asset.channel == "instagram-reels"
    assert asset.action_id == "publish-launch"
    assert asset.location == "exports/launch-video.mp4"


def test_campaign_asset_supports_cross_domain_deliverable_types() -> None:
    assets = (
        CampaignAsset("sermon-clip", "Sunday sermon clip", "video"),
        CampaignAsset("product-sheet", "Product comparison sheet", "document"),
        CampaignAsset("launch-page", "Campaign landing page", "landing-page"),
        CampaignAsset("radio-master", "Radio master", "audio"),
    )

    assert [asset.asset_type for asset in assets] == [
        "video",
        "document",
        "landing-page",
        "audio",
    ]


def test_campaign_asset_rejects_unknown_lifecycle_status() -> None:
    with pytest.raises(CampaignAssetError, match="status must be one of"):
        CampaignAsset("launch-video", "Launch video", "video", status="complete")


def test_campaign_asset_round_trips_serializable_metadata() -> None:
    asset = CampaignAsset(
        "launch-artwork",
        "Launch artwork",
        "image",
        status="approved",
        content_id="launch-announcement",
        channel="instagram",
    )

    assert CampaignAsset.from_dict(asset.to_dict()) == asset
