"""Campaign commands for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console

from ai.manager import AIManager
from core.config import ConfigurationError
from core.project import Project
from services.campaign import CampaignService
from services.campaign_generator import CampaignGeneratorService

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


@app.command("generate")
def generate_campaign(
    name: str = typer.Argument(..., help="Campaign or release name."),
    force: bool = typer.Option(False, "--force", help="Replace existing campaign content."),
) -> None:
    """Generate marketing assets for an existing campaign."""
    try:
        project = Project.discover()
        provider = AIManager(project.config.ai).default()
        paths = CampaignGeneratorService(project, provider).generate(name, force=force)
    except (ConfigurationError, FileExistsError, FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Generated {len(paths)} campaign assets[/bold green] "
        f"using {provider.name}."
    )
    for path in paths:
        console.print(f"- {path.relative_to(project.root)}")
