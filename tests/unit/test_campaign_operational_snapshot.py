from models.campaign_context import CampaignContext
from services.campaign_asset_readiness import AssetReadinessReport
from services.campaign_operational_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    CampaignOperationalSnapshotService,
)
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


def test_snapshot_has_stable_versioned_machine_readable_shape() -> None:
    snapshot = CampaignOperationalSnapshotService().build(make_report()).to_dict()

    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert snapshot["campaign"] == {
        "id": "autumn-launch",
        "name": "Autumn Launch",
        "type": "product-launch",
        "status": "active",
        "content_items": 3,
    }
    assert snapshot["execution"]["actions"] == 4
    assert snapshot["execution"]["open_actions"] == 2
    assert snapshot["execution"]["blocked_action_ids"] == ["publish-video"]
    assert snapshot["assets"]["total"] == 2
    assert snapshot["assets"]["ready"] == 2
    assert snapshot["attention"][0]["id"] == "publish-video"
    assert snapshot["attention"][0]["priority"] == 1
    assert snapshot["next_focus"]["id"] == "publish-video"


def test_snapshot_represents_ready_state_without_synthetic_focus() -> None:
    snapshot = CampaignOperationalSnapshotService().build(make_report(attention=False)).to_dict()

    assert snapshot["attention"] == ()
    assert snapshot["next_focus"] is None
    assert snapshot["execution"]["pending_action_ids"] == ["prepare-proof"]
