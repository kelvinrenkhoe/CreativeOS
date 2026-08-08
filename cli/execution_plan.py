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


def _parse_variables(values: list[str] | None) -> dict[str, str]:
    variables: dict[str, str] = {}
    for value in values or ():
        if "=" not in value:
            raise ValueError("--var must use key=value format")
        name, resolved = value.split("=", 1)
        name = name.strip().casefold()
        if not name or not resolved:
            raise ValueError("--var must use non-empty key=value format")
        if name in variables:
            raise ValueError(f"template variable {name!r} was supplied more than once")
        variables[name] = resolved
    return variables


def _render_plan(title: str, actions, *, show_milestone: bool = False) -> None:
    table = Table(title=title)
    table.add_column("ID")
    table.add_column("Action")
    table.add_column("Priority")
    table.add_column("Due")
    table.add_column("Channel")
    table.add_column("Milestone" if show_milestone else "Depends On")
    for action in actions:
        final_value = action.milestone or "-" if show_milestone else ", ".join(action.depends_on) or "-"
        table.add_row(
            action.action_id,
            action.title,
            action.priority,
            action.due_date.isoformat() if action.due_date else "-",
            action.channel or "-",
            final_value,
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
    variables: list[str] | None = typer.Option(  # noqa: B008
        None,
        "--var",
        help="Template variable in key=value form; repeat for multiple values.",
    ),
) -> None:
    """Validate and preview a template without writing campaign actions."""
    try:
        plan = _template_service(organization_id, project_id, campaign_id).plan(
            template_id,
            _parse_variables(variables),
        )
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
    _render_plan("Execution Plan Preview", plan.actions, show_milestone=True)
    console.print(f"Actions to create: {len(plan.actions)}")
    console.print("No changes written.")


@app.command("apply")
def apply(
    template_id: str = typer.Argument(..., help="Execution template identifier."),
    organization_id: str = typer.Option(..., "--org", help="Organization identifier."),
    project_id: str = typer.Option(..., "--project", help="Project identifier."),
    campaign_id: str = typer.Option(..., "--campaign", help="Campaign identifier."),
    variables: list[str] | None = typer.Option(  # noqa: B008
        None,
        "--var",
        help="Template variable in key=value form; repeat for multiple values.",
    ),
) -> None:
    """Validate, render, and persist all actions from an execution template."""
    try:
        service = _template_service(organization_id, project_id, campaign_id)
        created = service.apply(template_id, _parse_variables(variables))
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
