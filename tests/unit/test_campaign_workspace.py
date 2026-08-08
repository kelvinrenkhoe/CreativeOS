from pathlib import Path

from models.action import Action
from models.campaign_asset import CampaignAsset
from models.content_item import ContentItem
from models.creative_brief import ContentCreativeBrief
from services.action_repository import ActionRepository
from services.campaign_asset_repository import CampaignAssetRepository
from services.campaign_workspace import CampaignWorkspaceService
from services.content_inventory import ContentInventoryRepository


def make_campaign(tmp_path: Path) -> None:
    campaign_root = (
        tmp_path / "organizations" / "acme" / "projects" / "launch" / "campaigns" / "autumn-launch"
    )
    campaign_root.mkdir(parents=True)
    (campaign_root / "campaign.yaml").write_text(
        "id: autumn-launch\n"
        "name: Autumn Launch\n"
        "type: product-launch\n"
        "status: active\n"
        "objective: Build launch demand.\n"
        "channels:\n"
        "  - linkedin\n",
        encoding="utf-8",
    )


def test_workspace_composes_content_assets_and_actions(tmp_path: Path) -> None:
    make_campaign(tmp_path)
    content = ContentInventoryRepository(tmp_path, "acme", "launch", "autumn-launch")
    content.save(
        ContentItem(
            "launch-video",
            "Launch video",
            ContentCreativeBrief(
                objective="Introduce the product",
                audience="Prospective customers",
                key_message="The new product is available",
                call_to_action="Learn more",
            ),
            content_role="announce",
            content_format="video",
            channel="linkedin",
        )
    )
    content.save(
        ContentItem(
            "customer-proof",
            "Customer proof",
            ContentCreativeBrief(
                objective="Build trust",
                audience="Prospective customers",
                key_message="Customers see measurable value",
            ),
        )
    )

    assets = CampaignAssetRepository(tmp_path, "acme", "launch", "autumn-launch")
    assets.save(
        CampaignAsset(
            "launch-video-master",
            "Launch video master",
            "video",
            status="approved",
            content_id="launch-video",
        )
    )

    actions = ActionRepository(tmp_path, "acme", "launch", "autumn-launch")
    actions.save(Action("finalise-video", "Finalise launch video", status="completed"))
    actions.save(Action("publish-video", "Publish launch video", status="blocked"))
    actions.save(Action("prepare-proof", "Prepare customer proof", status="in-progress"))

    report = CampaignWorkspaceService(
        tmp_path,
        "acme",
        "launch",
        "autumn-launch",
    ).inspect()

    assert report.campaign.campaign_type == "product-launch"
    assert report.content_items == 2
    assert report.actions == 3
    assert report.completed_actions == 1
    assert report.blocked_action_ids == ("publish-video",)
    assert report.pending_action_ids == ("prepare-proof",)
    assert report.asset_readiness.total_assets == 1
    assert report.asset_readiness.ready_assets == 1
    assert report.asset_readiness.missing_location == ("launch-video-master",)
    assert report.content_gap_ids == ("customer-proof",)
    assert report.attention_ids == (
        "publish-video",
        "customer-proof",
        "launch-video-master",
    )


def test_empty_operational_campaign_has_stable_ready_view(tmp_path: Path) -> None:
    make_campaign(tmp_path)

    report = CampaignWorkspaceService(
        tmp_path,
        "acme",
        "launch",
        "autumn-launch",
    ).inspect()

    assert report.content_items == 0
    assert report.actions == 0
    assert report.open_actions == 0
    assert report.asset_readiness.ready_ratio == 1.0
    assert report.attention_ids == ()
