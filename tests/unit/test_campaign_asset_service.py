from pathlib import Path

import pytest

from models.campaign_asset import CampaignAsset
from services.campaign_asset_repository import CampaignAssetRepository
from services.campaign_asset_service import CampaignAssetService, CampaignAssetServiceError


def repository(tmp_path: Path) -> CampaignAssetRepository:
    return CampaignAssetRepository(tmp_path, "org", "project", "campaign")


def test_asset_lifecycle_transitions_are_deterministic(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.save(CampaignAsset("launch-video", "Launch Video", "video"))
    service = CampaignAssetService(repo)

    draft = service.transition("launch-video", "draft")
    review = service.transition("launch-video", "review")
    approved = service.transition("launch-video", "approved")
    published = service.transition("launch-video", "published")

    assert [draft.status, review.status, approved.status, published.status] == [
        "draft",
        "review",
        "approved",
        "published",
    ]
    assert repo.load("launch-video").status == "published"


def test_asset_lifecycle_rejects_skipped_transition(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.save(CampaignAsset("launch-video", "Launch Video", "video"))

    with pytest.raises(CampaignAssetServiceError, match="cannot transition"):
        CampaignAssetService(repo).transition("launch-video", "approved")


def test_asset_links_can_be_updated_without_changing_identity(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.save(CampaignAsset("launch-video", "Launch Video", "video"))
    service = CampaignAssetService(repo)

    linked = service.link_content("launch-video", "teaser-one")
    linked = service.link_action("launch-video", "publish-launch")
    linked = service.set_location("launch-video", "s3://campaign-assets/launch-video.mp4")

    assert linked.asset_id == "launch-video"
    assert linked.content_id == "teaser-one"
    assert linked.action_id == "publish-launch"
    assert linked.location == "s3://campaign-assets/launch-video.mp4"
    assert repo.load("launch-video") == linked


def test_review_can_return_to_draft_for_rework(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    repo.save(CampaignAsset("poster", "Launch Poster", "image", status="review"))

    updated = CampaignAssetService(repo).transition("poster", "draft")

    assert updated.status == "draft"
