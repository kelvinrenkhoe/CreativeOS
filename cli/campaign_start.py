"""Campaign-start command for CreativeOS."""

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.campaign_context import CampaignContextLoadError
from services.campaign_start import (
    DEFAULT_DOMAIN_PACK,
    CampaignStartError,
    CampaignStartService,
)
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
        raise CampaignStartError("campaign anchor date must use YYYY-MM-DD format") from exc


def _render_execution_preview(plan) -> None:
    table = Table(title="Recommended Execution Plan Preview")
    table.add_column("ID")
    table.add_column("Action")
    table.add_column("Due")
    table.add_column("Channel")
    table.add_column("Milestone")
    for action in plan.actions:
        table.add_row(
            action.action_id,
            action.title,
            action.due_date.isoformat() if action.due_date else "-",
            action.channel or "-",
            action.milestone or "-",
        )
    console.print(table)
    console.print(f"Actions proposed: {len(plan.actions)}")
    console.print("No execution actions written.")


def campaign_start_command(
    campaign_id: str = typer.Argument(..., help="Stable campaign identifier."),
    name: str = typer.Option(..., "--name", help="Campaign display name."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    anchor_date: str | None = typer.Option(
        None,
        "--anchor",
        help="Domain planning anchor date in YYYY-MM-DD format.",
    ),
    release_date: str | None = typer.Option(
        None,
        "--release",
        help="Legacy alias for --anchor used by music-release campaigns.",
    ),
    domain_pack: str = typer.Option(
        DEFAULT_DOMAIN_PACK,
        "--domain-pack",
        help="Registered domain pack used to resolve campaign execution defaults.",
    ),
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
    apply_execution: bool = typer.Option(
        False,
        "--apply-execution",
        help="Explicitly create the recommended actions after campaign creation and preview.",
    ),
) -> None:
    """Preview or create a domain-pack-backed campaign."""
    if apply_execution and not apply:
        console.print("[bold red]Error:[/bold red] --apply-execution requires --apply")
        raise typer.Exit(code=1)
    if anchor_date is not None and release_date is not None:
        console.print("[bold red]Error:[/bold red] provide --anchor or --release, not both")
        raise typer.Exit(code=1)
    supplied_anchor = anchor_date if anchor_date is not None else release_date
    if supplied_anchor is None:
        console.print("[bold red]Error:[/bold red] --anchor is required")
        raise typer.Exit(code=1)

    try:
        service = _service(organization_id, project_id)
        plan = service.plan(
            campaign_id,
            name,
            _parse_date(supplied_anchor),
            objective=objective,
            channels=tuple(channel),
            domain_pack_id=domain_pack,
        )
    except CLI_ERRORS as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    campaign = plan.campaign
    table = Table(title="Campaign Start")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Campaign", campaign.name)
    table.add_row("ID", campaign.campaign_id)
    table.add_row("Domain pack", plan.domain_pack_id)
    table.add_row(plan.anchor_name, plan.anchor_date.isoformat())
    table.add_row("Start", campaign.start_date.isoformat() if campaign.start_date else "-")
    table.add_row("End", campaign.end_date.isoformat() if campaign.end_date else "-")
    table.add_row("Channels", ", ".join(campaign.channels))
    table.add_row("Objective", campaign.objective)
    table.add_row("Recommended execution plan", plan.recommended_template_id)
    console.print(table)

    milestones = Table(title="Planned Milestones")
    milestones.add_column("Milestone")
    milestones.add_column("Date")
    for milestone_name, milestone_date in campaign.milestones:
        milestones.add_row(milestone_name, milestone_date.isoformat())
    console.print(milestones)

    if not apply:
        console.print("No changes written. Re-run with --apply to create this campaign.")
        console.print(
            "After creation, CreativeOS will preview the recommended execution actions "
            "without applying them."
        )
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

    try:
        execution_plan = service.preview_execution(plan)
    except CampaignStartError as exc:
        console.print(
            f"[bold yellow]Campaign created, but execution preview unavailable:[/bold yellow] {exc}"
        )
        return

    console.print(f"[bold]Recommended template[/bold] {execution_plan.template.name}")
    _render_execution_preview(execution_plan)

    if not apply_execution:
        console.print(
            "Execution remains unapplied. Re-run campaign start with --apply --apply-execution "
            "to create the proposed actions."
        )
        return

    try:
        created_actions = service.apply_execution(plan)
    except CampaignStartError as exc:
        console.print(f"[bold red]Execution apply failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Applied execution plan:[/bold green] {len(created_actions)} actions created"
    )
