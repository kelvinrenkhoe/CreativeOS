"""Operational campaign workspace command for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.action_repository import ActionRepositoryError
from services.campaign_asset_repository import CampaignAssetRepositoryError
from services.campaign_attention import CampaignAttentionService
from services.campaign_context import CampaignContextLoadError
from services.campaign_workspace import CampaignWorkspaceReport, CampaignWorkspaceService
from services.content_inventory import ContentInventoryError
from services.organization import OrganizationLoadError, OrganizationService
from services.project_context import ProjectContextLoadError

console = Console()
CLI_ERRORS = (
    OrganizationLoadError,
    ProjectContextLoadError,
    CampaignContextLoadError,
    ActionRepositoryError,
    CampaignAssetRepositoryError,
    ContentInventoryError,
    ValueError,
)


def _service(
    organization_id: str,
    project_id: str,
    campaign_id: str,
) -> CampaignWorkspaceService:
    repository_root = OrganizationService.discover(Path.cwd()).repository_root
    return CampaignWorkspaceService(
        repository_root,
        organization_id,
        project_id,
        campaign_id,
    )


def _summary_table(report: CampaignWorkspaceReport) -> Table:
    table = Table(title="Campaign Workspace")
    table.add_column("Area")
    table.add_column("Value")
    table.add_row("Campaign", report.campaign.name)
    table.add_row("Campaign ID", report.campaign.campaign_id)
    table.add_row("Type", report.campaign.campaign_type)
    table.add_row("Status", report.campaign.status)
    table.add_row("Content items", str(report.content_items))
    table.add_row("Actions", str(report.actions))
    table.add_row("Open actions", str(report.open_actions))
    table.add_row("Completed actions", str(report.completed_actions))
    table.add_row("Assets", str(report.asset_readiness.total_assets))
    table.add_row("Ready assets", str(report.asset_readiness.ready_assets))
    table.add_row("Asset readiness", f"{report.asset_readiness.ready_ratio:.0%}")
    return table


def _attention_table(report: CampaignWorkspaceReport) -> Table:
    table = Table(title="Prioritised Attention")
    table.add_column("Priority")
    table.add_column("Type")
    table.add_column("ID")
    table.add_column("Reason")

    items = CampaignAttentionService().prioritise(report)
    for item in items:
        table.add_row(
            f"P{item.priority}",
            item.kind,
            item.item_id,
            item.reason,
        )

    if not items:
        table.add_row("-", "Ready", "-", "No current attention items")

    return table


def campaign_workspace_command(
    campaign_id: str = typer.Argument(..., help="Campaign identifier."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
) -> None:
    """Display one campaign's operational workspace without changing state."""
    try:
        report = _service(organization_id, project_id, campaign_id).inspect()
    except CLI_ERRORS as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(_summary_table(report))
    console.print(_attention_table(report))

    if report.pending_action_ids:
        console.print(f"Pending work: {', '.join(report.pending_action_ids)}")
