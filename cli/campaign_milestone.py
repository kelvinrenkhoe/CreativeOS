"""Campaign milestone commands for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.campaign_milestone import (
    CampaignMilestoneService,
    CampaignMilestoneServiceError,
)
from services.organization import OrganizationLoadError, OrganizationService
from services.project_context import ProjectContextLoadError

app = typer.Typer(help="Inspect and manage campaign milestone dates.", no_args_is_help=True)
console = Console()
CLI_ERRORS = (
    OrganizationLoadError,
    ProjectContextLoadError,
    CampaignMilestoneServiceError,
    ValueError,
)


def _service(organization_id: str, project_id: str, campaign_id: str) -> CampaignMilestoneService:
    repository_root = OrganizationService.discover(Path.cwd()).repository_root
    return CampaignMilestoneService(
        repository_root,
        organization_id,
        project_id,
        campaign_id,
    )


def _handle_error(exc: Exception) -> None:
    console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


@app.command("list")
def list_milestones(
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """List named milestone dates for one campaign."""
    try:
        milestones = _service(organization_id, project_id, campaign_id).list()
    except CLI_ERRORS as exc:
        _handle_error(exc)

    table = Table(title="Campaign Milestones")
    table.add_column("Milestone")
    table.add_column("Date")
    for name, milestone_date in milestones:
        table.add_row(name, milestone_date.isoformat())
    console.print(table)
    if not milestones:
        console.print("No campaign milestones defined.")


@app.command("set")
def set_milestone(
    name: str = typer.Argument(..., help="Stable milestone name."),
    value: str = typer.Argument(..., help="Milestone date in YYYY-MM-DD format."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Create or update one campaign milestone."""
    try:
        campaign = _service(organization_id, project_id, campaign_id).set(name, value)
    except CLI_ERRORS as exc:
        _handle_error(exc)

    milestone_name = name.strip().casefold()
    milestone_date = campaign.milestone_dates[milestone_name]
    console.print(
        f"[bold green]Set milestone[/bold green] {milestone_name}: {milestone_date.isoformat()}"
    )


@app.command("remove")
def remove_milestone(
    name: str = typer.Argument(..., help="Milestone name to remove."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Remove one campaign milestone."""
    try:
        _service(organization_id, project_id, campaign_id).remove(name)
    except CLI_ERRORS as exc:
        _handle_error(exc)

    console.print(f"[bold green]Removed milestone[/bold green] {name}")
