"""Campaign manager CLI command."""

import typer
from rich.console import Console

from api.campaign_manager import CampaignManagerAPI
from cli.campaign import app as campaign_app
from core.config import ConfigurationError
from core.project import Project
from renderers.campaign_manager import CampaignManagerRenderer

console = Console()


def today_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Display the highest-priority campaign action for today."""
    try:
        project = Project.discover()
        result = CampaignManagerAPI(project).today(campaign_name)
    except ConfigurationError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignManagerRenderer().render(result))

    if result.errors:
        raise typer.Exit(code=1)


campaign_app.command("today")(today_command)
