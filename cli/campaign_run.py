"""Explicit provider-aware campaign runtime command."""

import typer
from rich.console import Console
from rich.table import Table

from cli import campaign as campaign_cli
from core.config import ConfigurationError
from services.in_memory_provider import InMemoryProviderExecutionAdapter
from services.provider_execution import ProviderExecutionAdapter

CLI_WORKER_ID = "creativeos-cli"
SUPPORTED_LOCAL_PROVIDER = "in-memory"
console = Console()


def _adapters_for(provider: str | None) -> tuple[ProviderExecutionAdapter, ...]:
    """Resolve an explicitly selected local provider adapter."""
    if provider is None:
        return ()

    normalized = provider.strip().casefold()
    if normalized != SUPPORTED_LOCAL_PROVIDER:
        raise ValueError(
            f"unsupported execution provider: {provider}. "
            f"Supported providers: {SUPPORTED_LOCAL_PROVIDER}"
        )
    return (InMemoryProviderExecutionAdapter(),)


def campaign_run_command(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Explicit execution provider. Use 'in-memory' for deterministic local execution.",
    ),
) -> None:
    """Advance at most one safe campaign runtime action."""
    try:
        project = campaign_cli.Project.discover()
        adapters = _adapters_for(provider)
    except (ConfigurationError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if adapters:
        api = campaign_cli.CampaignRunnerAPI(
            project,
            adapters=adapters,
            worker_id=CLI_WORKER_ID,
        )
    else:
        api = campaign_cli.CampaignRunnerAPI(
            project,
            worker_id=CLI_WORKER_ID,
        )

    result = api.advance(campaign_id)
    if result.errors:
        for error in result.errors:
            console.print(f"[bold red]Error:[/bold red] {error}")
        raise typer.Exit(code=1)

    table = Table(
        title="Campaign Runtime Action",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_row("Campaign ID", result.campaign_id)
    table.add_row("Provider", provider or "None configured")
    table.add_row("Stage", result.stage or "Unknown")
    table.add_row("Action", result.action or "None")
    table.add_row("Request ID", result.request_id or "None")
    table.add_row("Paused", "Yes" if result.paused else "No")
    console.print(table)
