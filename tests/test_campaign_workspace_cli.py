"""Tests for the operational campaign workspace command."""

from typer.testing import CliRunner

from cli import campaign_workspace as workspace_cli
from cli.main import app
from models.campaign_context import CampaignContext
from services.campaign_asset_readiness import AssetReadinessReport
from services.campaign_workspace import CampaignWorkspaceReport

runner = CliRunner()


class FakeWorkspaceService:
    def __init__(self, report: CampaignWorkspaceReport) -> None:
        self.report = report

    def inspect(self) -> CampaignWorkspaceReport:
        return self.report


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


def test_workspace_command_renders_operational_summary(monkeypatch) -> None:
    report = make_report()
    monkeypatch.setattr(
        workspace_cli,
        "_service",
        lambda organization_id, project_id, campaign_id: FakeWorkspaceService(report),
    )

    result = runner.invoke(
        app,
        [
            "campaign",
            "workspace",
            "autumn-launch",
            "--org",
            "acme",
            "--project",
            "launch",
        ],
    )

    assert result.exit_code == 0
    assert "Campaign Workspace" in result.stdout
    assert "Autumn Launch" in result.stdout
    assert "product-launch" in result.stdout
    assert "100%" in result.stdout
    assert "publish-video" in result.stdout
    assert "customer-proof" in result.stdout
    assert "launch-video-master" in result.stdout
    assert "Pending work: prepare-proof" in result.stdout


def test_workspace_command_renders_ready_attention_state(monkeypatch) -> None:
    report = make_report(attention=False)
    monkeypatch.setattr(
        workspace_cli,
        "_service",
        lambda organization_id, project_id, campaign_id: FakeWorkspaceService(report),
    )

    result = runner.invoke(
        app,
        [
            "campaign",
            "workspace",
            "autumn-launch",
            "--org",
            "acme",
            "--project",
            "launch",
        ],
    )

    assert result.exit_code == 0
    assert "Needs Attention" in result.stdout
    assert "No current attention items" in result.stdout
