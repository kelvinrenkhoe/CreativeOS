"""Render deterministic creator-facing AI campaign plans."""

import typer
from rich.console import Console
from rich.table import Table

from api.ai_campaign_planner import AICampaignPlannerAPI

console = Console()


def campaign_plan_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Display a structured four-week AI campaign rollout plan."""
    try:
        plan = AICampaignPlannerAPI().plan(campaign_name)
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]AI Campaign Plan: {plan.campaign_name}[/bold]")
    summary = Table(show_header=False)
    summary.add_row("Duration", f"{plan.duration_days} days")
    summary.add_row("Objectives", str(len(plan.objectives)))
    summary.add_row("Weeks", str(len(plan.weeks)))
    console.print(summary)

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
