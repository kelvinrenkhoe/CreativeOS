from models.campaign_context import CampaignContext
from services.campaign_asset_readiness import AssetReadinessReport
from services.campaign_next_focus import CampaignNextFocusService
from services.campaign_workspace import CampaignWorkspaceReport


def make_report(*, attention: bool = True) -> CampaignWorkspaceReport:
    return CampaignWorkspaceReport(
        campaign=CampaignContext(
            campaign_id="autumn-launch",
            name="Autumn Launch",
            campaign_type="product-launch",
            status="active",
        ),
        content_items=3,
        actions=4,
        completed_actions=1,
        blocked_action_ids=("publish-video",) if attention else (),
        pending_action_ids=("prepare-proof",),
        asset_readiness=AssetReadinessReport(
            total_assets=2,
            planned=0,
            draft=0,
            review=0,
            approved=1,
            published=1,
            unlinked_content=(),
            missing_location=("launch-video-master",) if attention else (),
        ),
        content_gap_ids=("customer-proof",) if attention else (),
    )


def test_next_focus_selects_highest_priority_attention_item() -> None:
    recommendation = CampaignNextFocusService().recommend(make_report())

    assert recommendation.item is not None
    assert recommendation.item.item_id == "publish-video"
    assert recommendation.item.priority == 1
    assert recommendation.pending_action_ids == ("prepare-proof",)
    assert recommendation.ready is False


def test_next_focus_is_ready_when_no_attention_exists() -> None:
    recommendation = CampaignNextFocusService().recommend(make_report(attention=False))

    assert recommendation.item is None
    assert recommendation.pending_action_ids == ("prepare-proof",)
    assert recommendation.ready is True
