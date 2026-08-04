"""Campaign planner CLI command."""

import typer
from rich.console import Console

from api.campaign_planner import CampaignPlannerAPI
from cli.campaign import app as campaign_app
from core.config import ConfigurationError
from core.project import Project
from renderers.campaign_planner import CampaignPlannerRenderer

console = Console()


def plan_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
    days: int = typer.Option(7, "--days", min=1, help="Number of days to plan."),
) -> None:
    """Display a deterministic multi-day campaign execution plan."""
    try:
        project = Project.discover()
        result = CampaignPlannerAPI(project).plan(campaign_name, days=days)
    except ConfigurationError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignPlannerRenderer().render(result))

    if result.errors:
        raise typer.Exit(code=1)


campaign_app.command("plan")(plan_command)
