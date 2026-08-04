"""Campaign release timeline CLI command."""

import typer
from rich.console import Console

from api.campaign_timeline import CampaignTimelineAPI
from cli.campaign import app as campaign_app
from core.config import ConfigurationError
from core.project import Project
from renderers.campaign_release_timeline import CampaignReleaseTimelineRenderer

console = Console()


def timeline_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Display the deterministic release timeline for a campaign."""
    try:
        project = Project.discover()
        result = CampaignTimelineAPI(project).timeline(campaign_name)
    except ConfigurationError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.errors:
        for error in result.errors:
            console.print(f"[bold red]Error:[/bold red] {error}")
        raise typer.Exit(code=1)

    console.print(CampaignReleaseTimelineRenderer().render(result))


campaign_app.command("timeline")(timeline_command)
