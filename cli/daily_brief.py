"""Top-level Daily Brief command for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console

from renderers.daily_brief import DailyBriefRenderer
from services.action_repository import ActionRepositoryError
from services.action_service import ActionServiceError
from services.campaign_context import CampaignContextLoadError
from services.daily_brief import DailyBriefService
from services.organization import OrganizationLoadError, OrganizationService
from services.project_context import ProjectContextLoadError

console = Console()


def today_command(
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Show the campaign Daily Brief for today."""
    try:
        repository_root = OrganizationService.discover(Path.cwd()).repository_root
        brief = DailyBriefService(
            repository_root,
            organization_id,
            project_id,
            campaign_id,
        ).build()
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ValueError,
    ) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(DailyBriefRenderer().render(brief))
