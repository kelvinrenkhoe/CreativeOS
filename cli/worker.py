"""Background campaign worker commands."""

import typer
from rich.console import Console
from rich.table import Table

from cli import campaign as campaign_cli
from cli.campaign_run import _adapters_for
from core.config import ConfigurationError
from services.campaign_worker import CampaignWorkerAPI

app = typer.Typer(help="Process persisted campaigns without interactive input.")
console = Console()


def _worker(provider: str | None, max_steps: int) -> CampaignWorkerAPI:
    project = campaign_cli.Project.discover()
    return CampaignWorkerAPI.for_project(
        project,
        adapters=_adapters_for(provider),
        max_steps=max_steps,
    )


@app.command("status")
def worker_status_command() -> None:
    """Display unfinished and completed persisted campaign runs."""
    try:
        project = campaign_cli.Project.discover()
        status = CampaignWorkerAPI.for_project(project).status()
    except (ConfigurationError, OSError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Campaign Worker Status", show_header=False, box=None, pad_edge=False)
    table.add_row("State", "idle" if status.idle else "work available")
    table.add_row("Pending campaigns", str(len(status.pending)))
    table.add_row("Completed campaigns", str(len(status.completed)))
    console.print(table)

    if status.pending:
        pending = Table(title="Pending Campaigns")
        pending.add_column("Campaign ID", no_wrap=True)
        pending.add_column("Work", no_wrap=True)
        pending.add_column("Stage", no_wrap=True)
        for run in status.pending:
            pending.add_row(run.campaign_id, run.plan.work_name, run.stage)
        console.print(pending)


@app.command("run-once")
def worker_run_once_command(
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Explicit execution provider. Use 'in-memory' for deterministic local execution.",
    ),
    max_steps: int = typer.Option(
        100,
        "--max-steps",
        min=1,
        help="Maximum safe actions for the selected campaign.",
    ),
) -> None:
    """Advance at most one unfinished campaign and then exit."""
    try:
        result = _worker(provider, max_steps).run_once()
    except (ConfigurationError, OSError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if result.idle:
        console.print("Campaign worker is idle; no unfinished campaigns were found.")
        return

    orchestration = result.orchestration
    if orchestration is None:
        console.print("[bold red]Error:[/bold red] worker produced no orchestration result")
        raise typer.Exit(code=1)

    table = Table(title="Campaign Worker Run", show_header=False, box=None, pad_edge=False)
    table.add_row("Campaign ID", result.campaign_id or "-")
    table.add_row("Steps", str(orchestration.steps))
    table.add_row("Completed", "Yes" if orchestration.completed else "No")
    table.add_row("Paused", "Yes" if orchestration.paused else "No")
    table.add_row("Uncertain", "Yes" if orchestration.uncertain else "No")
    console.print(table)

    for warning in orchestration.warnings:
        console.print(f"[bold yellow]Warning:[/bold yellow] {warning}")
    for error in orchestration.errors:
        console.print(f"[bold red]Error:[/bold red] {error}")

    if orchestration.errors or orchestration.uncertain:
        raise typer.Exit(code=1)
