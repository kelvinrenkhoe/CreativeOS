"""Read-only CLI for persisted campaign orchestration history."""

import typer
from rich.console import Console
from rich.table import Table

from api.persisted_campaign_orchestrator import ORCHESTRATION_EVENTS_PATH
from cli import campaign as campaign_cli
from core.config import ConfigurationError
from services.campaign_orchestration_events import (
    JsonOrchestrationEventStore,
    OrchestrationEventStoreError,
    StoredOrchestrationEvent,
)

console = Console()


def _render_history(
    campaign_id: str,
    events: tuple[StoredOrchestrationEvent, ...],
) -> None:
    table = Table(title=f"Campaign Orchestration History: {campaign_id}")
    table.add_column("Run ID")
    table.add_column("Policy")
    table.add_column("Seq", justify="right")
    table.add_column("Step", justify="right")
    table.add_column("Event")
    table.add_column("Stage")
    table.add_column("Action")
    table.add_column("Request ID")
    table.add_column("Detail")

    for event in events:
        table.add_row(
            event.run_id,
            event.policy,
            str(event.sequence),
            str(event.step),
            event.kind,
            event.stage or "-",
            event.action or "-",
            event.request_id or "-",
            event.detail or "-",
        )
    console.print(table)


def campaign_history_command(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Show only one persisted orchestration run.",
    ),
) -> None:
    """Display durable orchestration events for a campaign."""
    try:
        project = campaign_cli.Project.discover()
        store = JsonOrchestrationEventStore(project.root / ORCHESTRATION_EVENTS_PATH)
        events = store.load(campaign_id)
    except (ConfigurationError, OrchestrationEventStoreError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if run_id is not None:
        events = tuple(event for event in events if event.run_id == run_id)

    if not events:
        suffix = f" for run {run_id}" if run_id else ""
        console.print(f"No orchestration history found for {campaign_id}{suffix}.")
        return

    _render_history(campaign_id, events)
