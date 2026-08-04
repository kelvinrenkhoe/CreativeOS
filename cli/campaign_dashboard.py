"""Campaign dashboard CLI command."""

import typer
from rich.console import Console

from api.campaign_dashboard import CampaignDashboardAPI
from cli.campaign import app as campaign_app
from core.config import ConfigurationError
from core.project import Project
from renderers.campaign_dashboard import CampaignDashboardRenderer

console = Console()


def dashboard_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Display an aggregated campaign dashboard."""
    try:
        project = Project.discover()
        result = CampaignDashboardAPI(project).summary(campaign_name)
    except ConfigurationError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignDashboardRenderer().render(result))

    if result.errors:
        raise typer.Exit(code=1)


campaign_app.command("dashboard")(dashboard_command)
