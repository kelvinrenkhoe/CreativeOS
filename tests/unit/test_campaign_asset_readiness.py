from models.campaign_asset import CampaignAsset
from services.campaign_asset_readiness import CampaignAssetReadinessService


def test_asset_readiness_summarises_status_and_linkage_gaps() -> None:
    assets = (
        CampaignAsset("video-one", "Video One", "video", status="planned"),
        CampaignAsset(
            "video-two",
            "Video Two",
            "video",
            status="approved",
            content_id="teaser-two",
        ),
        CampaignAsset(
            "poster",
            "Poster",
            "image",
            status="published",
            content_id="launch-poster",
            location="https://example.test/poster",
        ),
    )

    report = CampaignAssetReadinessService().inspect(assets)

    assert report.total_assets == 3
    assert report.planned == 1
    assert report.approved == 1
    assert report.published == 1
    assert report.ready_assets == 2
    assert report.ready_ratio == 2 / 3
    assert report.unlinked_content == ("video-one",)
    assert report.missing_location == ("video-two",)


def test_empty_asset_set_is_ready_by_definition() -> None:
    report = CampaignAssetReadinessService().inspect(())

    assert report.total_assets == 0
    assert report.ready_ratio == 1.0
    assert report.unlinked_content == ()
    assert report.missing_location == ()
