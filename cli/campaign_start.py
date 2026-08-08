"""Campaign-start command for CreativeOS."""

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.campaign_context import CampaignContextLoadError
from services.campaign_start import CampaignStartError, CampaignStartService
from services.organization import OrganizationLoadError, OrganizationService
from services.project_context import ProjectContextLoadError

console = Console()
CLI_ERRORS = (
    OrganizationLoadError,
    ProjectContextLoadError,
    CampaignContextLoadError,
    CampaignStartError,
    ValueError,
)


def _service(organization_id: str, project_id: str) -> CampaignStartService:
    repository_root = OrganizationService.discover(Path.cwd()).repository_root
    return CampaignStartService(repository_root, organization_id, project_id)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CampaignStartError("release date must use YYYY-MM-DD format") from exc


def campaign_start_command(
    campaign_id: str = typer.Argument(..., help="Stable campaign identifier."),
    name: str = typer.Option(..., "--name", help="Campaign display name."),
    release_date: str = typer.Option(..., "--release", help="Release date in YYYY-MM-DD format."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    objective: str = typer.Option(
        "Build awareness and coordinate release execution.",
        "--objective",
        help="Primary campaign objective.",
    ),
    channel: list[str] = typer.Option(  # noqa: B008
        ...,
        "--channel",
        help="Campaign channel; repeat for multiple channels.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Create the campaign after previewing the deterministic plan.",
    ),
) -> None:
    """Preview or create a milestone-ready music-release campaign."""
    try:
        service = _service(organization_id, project_id)
        plan = service.plan(
            campaign_id,
            name,
            _parse_date(release_date),
            objective=objective,
            channels=tuple(channel),
        )
    except CLI_ERRORS as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    campaign = plan.campaign
    table = Table(title="Music Release Campaign Start")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Campaign", campaign.name)
    table.add_row("ID", campaign.campaign_id)
    table.add_row("Release", plan.release_date.isoformat())
    table.add_row("Start", campaign.start_date.isoformat() if campaign.start_date else "-")
    table.add_row("End", campaign.end_date.isoformat() if campaign.end_date else "-")
    table.add_row("Channels", ", ".join(campaign.channels))
    table.add_row("Objective", campaign.objective)
    console.print(table)

    milestones = Table(title="Planned Milestones")
    milestones.add_column("Milestone")
    milestones.add_column("Date")
    for milestone_name, milestone_date in campaign.milestones:
        milestones.add_row(milestone_name, milestone_date.isoformat())
    console.print(milestones)

    if not apply:
        console.print("No changes written. Re-run with --apply to create this campaign.")
        return

    try:
        created = service.apply(plan)
    except (CampaignStartError, OSError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Created campaign:[/bold green] {created.campaign_id} "
        f"({created.campaign_type})"
    )
