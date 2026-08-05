"""Render creator-facing AI campaign plans."""

import typer
from rich.console import Console
from rich.table import Table

from ai.manager import AIManager
from api.ai_campaign_planner import AICampaignPlannerAPI
from core.config import ConfigurationError
from core.project import Project

console = Console()


def campaign_plan_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
    deterministic: bool = typer.Option(
        False,
        "--deterministic",
        help="Use the offline deterministic planner instead of the configured AI provider.",
    ),
) -> None:
    """Display a structured four-week AI campaign rollout plan."""
    try:
        provider = None
        provider_name = "deterministic"
        if not deterministic:
            project = Project.discover()
            configured = AIManager(project.config.ai).default()
            provider_name = configured.name
            if configured.name != "mock":
                provider = configured

        plan = AICampaignPlannerAPI(provider=provider).plan(campaign_name)
    except (ConfigurationError, KeyError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if plan.errors:
        for error in plan.errors:
            console.print(f"[bold red]Error:[/bold red] {error}")
        raise typer.Exit(code=1)

    console.print(f"[bold]AI Campaign Plan: {plan.campaign_name}[/bold]")
    summary = Table(show_header=False)
    summary.add_row("Provider", provider_name)
    summary.add_row("Duration", f"{plan.duration_days} days")
    summary.add_row("Objectives", str(len(plan.objectives)))
    summary.add_row("Weeks", str(len(plan.weeks)))
    console.print(summary)

    if plan.warnings:
        warnings = Table(title="Warnings")
        warnings.add_column("Warning")
        for warning in plan.warnings:
            warnings.add_row(warning)
        console.print(warnings)

    objectives = Table(title="Objectives")
    objectives.add_column("Objective")
    for objective in plan.objectives:
        objectives.add_row(objective.title)
    console.print(objectives)

    for week in plan.weeks:
        table = Table(title=f"Week {week.number}: {week.objective}")
        table.add_column("Task", no_wrap=True)
        table.add_column("Description")
        for task in week.tasks:
            table.add_row(task.title, task.description)
        console.print(table)
