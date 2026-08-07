"""Organization commands for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.organization import OrganizationLoadError, OrganizationService

app = typer.Typer(help="Manage CreativeOS organizations.", no_args_is_help=True)
console = Console()


def _service() -> OrganizationService:
    """Discover the current repository and return its organization service."""
    return OrganizationService.discover(Path.cwd())


@app.command("list")
def list_organizations() -> None:
    """List organizations in the current CreativeOS repository."""
    try:
        organizations = _service().list()
    except OrganizationLoadError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="CreativeOS Organizations")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Type")

    for organization in organizations:
        table.add_row(
            organization.organization_id,
            organization.name,
            organization.organization_type.value,
        )

    console.print(table)


@app.command("show")
def show_organization(
    organization_id: str = typer.Argument(..., help="Organization identifier."),
) -> None:
    """Show one organization."""
    try:
        organization = _service().load(organization_id)
    except OrganizationLoadError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="CreativeOS Organization", show_header=False, box=None)
    table.add_row("ID", organization.organization_id)
    table.add_row("Name", organization.name)
    table.add_row("Type", organization.organization_type.value)
    if organization.description:
        table.add_row("Description", organization.description)
    console.print(table)


@app.command("validate")
def validate_organizations() -> None:
    """Validate every organization in the current repository."""
    try:
        service = _service()
        organizations = service.list()
        for organization in organizations:
            service.organization_path(organization.organization_id)
    except OrganizationLoadError as exc:
        console.print(f"[bold red]Invalid:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Valid:[/bold green] {len(organizations)} organization(s)")
