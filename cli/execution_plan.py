"""Reusable execution plan template commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.action_repository import ActionRepository, ActionRepositoryError
from services.action_service import ActionService, ActionServiceError
from services.campaign_context import CampaignContextLoadError
from services.execution_template import ExecutionTemplateService, ExecutionTemplateServiceError
from services.organization import OrganizationLoadError, OrganizationService
from services.project_context import ProjectContextLoadError

app = typer.Typer(help="Preview and apply reusable execution plans.", no_args_is_help=True)
console = Console()


def _template_service(
    organization_id: str,
    project_id: str,
    campaign_id: str,
) -> ExecutionTemplateService:
    repository_root = OrganizationService.discover(Path.cwd()).repository_root
    repository = ActionRepository(repository_root, organization_id, project_id, campaign_id)
    return ExecutionTemplateService(repository_root, ActionService(repository))


def _render_plan(title: str, actions) -> None:
    table = Table(title=title)
    table.add_column("ID")
    table.add_column("Action")
    table.add_column("Priority")
    table.add_column("Depends On")
    for action in actions:
        table.add_row(
            action.action_id,
            action.title,
            action.priority,
            ", ".join(action.depends_on) or "-",
        )
    console.print(table)


def _handle_error(exc: Exception) -> None:
    console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


@app.command("preview")
def preview(
    template_id: str = typer.Argument(..., help="Execution template identifier."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Validate and preview a template without writing campaign actions."""
    try:
        plan = _template_service(organization_id, project_id, campaign_id).plan(template_id)
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ExecutionTemplateServiceError,
        ValueError,
    ) as exc:
        _handle_error(exc)
    console.print(f"[bold]Template[/bold] {plan.template.name}")
    _render_plan("Execution Plan Preview", plan.actions)
    console.print(f"Actions to create: {len(plan.actions)}")
    console.print("No changes written.")


@app.command("apply")
def apply(
    template_id: str = typer.Argument(..., help="Execution template identifier."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
) -> None:
    """Validate and persist all actions from an execution template."""
    try:
        service = _template_service(organization_id, project_id, campaign_id)
        created = service.apply(template_id)
    except (
        OrganizationLoadError,
        ProjectContextLoadError,
        CampaignContextLoadError,
        ActionRepositoryError,
        ActionServiceError,
        ExecutionTemplateServiceError,
        ValueError,
    ) as exc:
        _handle_error(exc)
    _render_plan("Created Actions", created)
    console.print(f"[bold green]Applied[/bold green] {template_id}: {len(created)} actions created")
