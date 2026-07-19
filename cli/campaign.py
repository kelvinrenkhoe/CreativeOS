"""Campaign commands for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console

from core.config import ConfigurationError
from core.project import Project
from services.campaign import CampaignService

app = typer.Typer(help="Create and manage music marketing campaigns.", no_args_is_help=True)
console = Console()


@app.command("create")
def create_campaign(
    name: str = typer.Argument(..., help="Campaign or release name."),
    artist: str | None = typer.Option(None, "--artist", help="Override the configured artist."),
) -> None:
    """Create a complete campaign workspace."""
    try:
        project = Project.discover()
        path: Path = CampaignService(project).create(name, artist=artist)
    except (ConfigurationError, FileExistsError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Created campaign:[/bold green] {path}")
