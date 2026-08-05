"""Inspect and reconcile durable campaign runtime checkpoints."""

from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.table import Table

from api.campaign_runner import CHECKPOINTS_PATH
from cli import campaign as campaign_cli
from core.config import ConfigurationError
from services.runtime_checkpoints import (
    JsonRuntimeCheckpointStore,
    RuntimeCheckpoint,
    RuntimeCheckpointError,
)

app = typer.Typer(help="Inspect and reconcile campaign runtime checkpoints.")
console = Console()


def _store() -> JsonRuntimeCheckpointStore:
    project = campaign_cli.Project.discover()
    return JsonRuntimeCheckpointStore(project.root / CHECKPOINTS_PATH)


def _campaign_checkpoints(
    store: JsonRuntimeCheckpointStore,
    campaign_id: str,
) -> tuple[RuntimeCheckpoint, ...]:
    return tuple(checkpoint for checkpoint in store.load() if checkpoint.campaign_id == campaign_id)


def _checkpoint_table(checkpoint: RuntimeCheckpoint, *, title: str) -> Table:
    table = Table(title=title, show_header=False, box=None, pad_edge=False)
    table.add_column("Field", no_wrap=True)
    table.add_column("Value")
    table.add_row("Checkpoint ID", checkpoint.checkpoint_id)
    table.add_row("Action Key", checkpoint.action_key)
    table.add_row("Status", checkpoint.status)
    table.add_row("Started", checkpoint.started_at.isoformat())
    table.add_row(
        "Completed",
        checkpoint.completed_at.isoformat() if checkpoint.completed_at else "-",
    )
    table.add_row("Result Action", checkpoint.result_action or "-")
    table.add_row("Stage", checkpoint.resulting_stage or "-")
    table.add_row("Request ID", checkpoint.request_id or "-")
    return table


@app.command("status")
def checkpoint_status_command(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
) -> None:
    """Display durable checkpoints for one campaign."""
    try:
        checkpoints = _campaign_checkpoints(_store(), campaign_id)
    except (ConfigurationError, OSError, RuntimeCheckpointError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if not checkpoints:
        console.print(f"No runtime checkpoints found for {campaign_id}.")
        return

    for index, checkpoint in enumerate(checkpoints, start=1):
        console.print(
            _checkpoint_table(
                checkpoint,
                title=f"Campaign Runtime Checkpoints: {campaign_id} ({index}/{len(checkpoints)})",
            )
        )


@app.command("reconcile")
def checkpoint_reconcile_command(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
    decision: str = typer.Option(
        ...,
        "--decision",
        help="Either confirm-completed or confirm-not-completed.",
    ),
    result_action: str | None = typer.Option(
        None,
        "--result-action",
        help="Verified action result when confirming completion.",
    ),
    resulting_stage: str | None = typer.Option(
        None,
        "--resulting-stage",
        help="Verified resulting stage when confirming completion.",
    ),
    request_id: str | None = typer.Option(
        None,
        "--request-id",
        help="Verified provider request ID when available.",
    ),
) -> None:
    """Explicitly resolve one uncertain campaign runtime checkpoint."""
    try:
        store = _store()
        uncertain = tuple(
            checkpoint
            for checkpoint in _campaign_checkpoints(store, campaign_id)
            if checkpoint.status == "uncertain"
        )
        if not uncertain:
            raise RuntimeCheckpointError(f"campaign {campaign_id} has no uncertain checkpoint")
        if len(uncertain) > 1:
            raise RuntimeCheckpointError(
                f"campaign {campaign_id} has multiple uncertain checkpoints"
            )
        updated = store.reconcile(
            uncertain[0],
            decision=decision,
            now=datetime.now(UTC),
            result_action=result_action,
            request_id=request_id,
            resulting_stage=resulting_stage,
        )
    except (ConfigurationError, OSError, RuntimeCheckpointError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"Checkpoint {updated.checkpoint_id} reconciled as {updated.status}.")
