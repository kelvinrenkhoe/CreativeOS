"""Execution Engine commands for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from models.action import Action
from services.action_repository import ActionRepository, ActionRepositoryError
from services.action_service import ActionService, ActionServiceError
from services.campaign_context import CampaignContextLoadError
from services.execution_planner import ExecutionPlanner
from services.organization import OrganizationLoadError, OrganizationService
from services.project_context import ProjectContextLoadError

app = typer.Typer(help="Plan campaign execution work.", no_args_is_help=True)
console = Console()


def _planner(organization_id: str, project_id: str, campaign_id: str) -> ExecutionPlanner:
    """Build an execution planner for one campaign in the current repository."""
    repository_root = OrganizationService.discover(Path.cwd()).repository_root
    repository = ActionRepository(
        repository_root,
        organization_id,
        project_id,
        campaign_id,
    )
    return ExecutionPlanner(ActionService(repository))


def _render_actions(title: str, actions: tuple[Action, ...]) -> None:
    table = Table(title=title)
    table.add_column("ID")
    table.add_column("Action")
    table.add_column("Priority")
    table.add_column("Due")
    table.add_column("Channel")

    for action in actions:
        table.add_row(
            action.action_id,
            action.title,
            action.priority,
            action.due_date.isoformat() if action.due_date else "-",
            action.channel or "-",
        )

    console.print(table)


def _handle_error(exc: Exception) -> None:
    console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


@app.command("today")
def today(
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Show work due today, overdue work, blocked work, and campaign progress."""
    try:
        plan = _planner(organization_id, project_id, campaign_id).plan()
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ValueError,
    ) as exc:
        _handle_error(exc)

    console.print(
        f"[bold]Execution Context[/bold] {organization_id} / {project_id} / {campaign_id}"
    )
    _render_actions("Overdue", plan.overdue)
    _render_actions("Due Today", plan.today)
    _render_actions("Blocked", plan.blocked)
    console.print(
        f"Progress: {plan.progress.completed}/{plan.progress.total} ({plan.progress.percent:.1f}%)"
    )


@app.command("next")
def next_actions(
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
    limit: int = typer.Option(3, "--limit", min=1, help="Maximum actions to return."),
) -> None:
    """Show the highest-value ready work to do next."""
    try:
        actions = _planner(organization_id, project_id, campaign_id).next(limit=limit)
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ValueError,
    ) as exc:
        _handle_error(exc)

    _render_actions("Next Actions", actions)


@app.command("overdue")
def overdue(
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Show unfinished campaign actions that are overdue."""
    try:
        actions = _planner(organization_id, project_id, campaign_id).plan().overdue
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ValueError,
    ) as exc:
        _handle_error(exc)

    _render_actions("Overdue Actions", actions)


@app.command("ready")
def ready(
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Show actions whose dependencies are satisfied and can be worked now."""
    try:
        actions = _planner(organization_id, project_id, campaign_id).plan().ready
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ValueError,
    ) as exc:
        _handle_error(exc)

    _render_actions("Ready Actions", actions)
