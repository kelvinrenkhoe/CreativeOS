from models.campaign_context import CampaignContext
from services.campaign_asset_readiness import AssetReadinessReport
from services.campaign_attention import CampaignAttentionService
from services.campaign_workspace import CampaignWorkspaceReport


def make_report() -> CampaignWorkspaceReport:
    return CampaignWorkspaceReport(
        campaign=CampaignContext(
            campaign_id="autumn-launch",
            name="Autumn Launch",
            campaign_type="product-launch",
            status="active",
        ),
        content_items=3,
        actions=3,
        completed_actions=1,
        blocked_action_ids=("publish-video", "approve-copy"),
        pending_action_ids=("prepare-proof",),
        asset_readiness=AssetReadinessReport(
            total_assets=2,
            planned=0,
            draft=0,
            review=0,
            approved=1,
            published=1,
            unlinked_content=(),
            missing_location=("launch-video-master",),
        ),
        content_gap_ids=("customer-proof",),
    )


def test_attention_prioritises_blockers_then_assets_then_metadata() -> None:
    items = CampaignAttentionService().prioritise(make_report())

    assert [(item.priority, item.kind, item.item_id) for item in items] == [
        (1, "blocked-action", "approve-copy"),
        (1, "blocked-action", "publish-video"),
        (2, "asset-location", "launch-video-master"),
        (3, "content-metadata", "customer-proof"),
    ]
    assert all(item.reason for item in items)


def test_attention_is_empty_when_workspace_requires_no_attention() -> None:
    report = CampaignWorkspaceReport(
        campaign=CampaignContext(
            campaign_id="ready-campaign",
            name="Ready Campaign",
            campaign_type="custom",
            status="active",
        ),
        content_items=0,
        actions=0,
        completed_actions=0,
        blocked_action_ids=(),
        pending_action_ids=(),
        asset_readiness=AssetReadinessReport(
            total_assets=0,
            planned=0,
            draft=0,
            review=0,
            approved=0,
            published=0,
            unlinked_content=(),
            missing_location=(),
        ),
        content_gap_ids=(),
    )

    assert CampaignAttentionService().prioritise(report) == ()
