"""Provider-aware campaign orchestration command."""

import typer
from rich.console import Console
from rich.table import Table

from api.campaign_orchestrator import (
    POLICY_ONCE,
    POLICY_UNTIL_BLOCKED,
    POLICY_UNTIL_COMPLETE,
    CampaignOrchestratorAPI,
)
from api.persisted_campaign_orchestrator import PersistedCampaignOrchestratorAPI
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


def _policy_for(*, once: bool, until_blocked: bool, until_complete: bool) -> str:
    """Resolve one mutually exclusive orchestration policy."""
    selected = tuple(
        policy
        for enabled, policy in (
            (once, POLICY_ONCE),
            (until_blocked, POLICY_UNTIL_BLOCKED),
            (until_complete, POLICY_UNTIL_COMPLETE),
        )
        if enabled
    )
    if len(selected) > 1:
        raise ValueError("choose only one of --once, --until-blocked, or --until-complete")
    return selected[0] if selected else POLICY_ONCE


def _runner(project, adapters: tuple[ProviderExecutionAdapter, ...]):
    """Build the existing runner while preserving its test injection boundary."""
    if adapters:
        return campaign_cli.CampaignRunnerAPI(
            project,
            adapters=adapters,
            worker_id=CLI_WORKER_ID,
        )
    return campaign_cli.CampaignRunnerAPI(project, worker_id=CLI_WORKER_ID)


def _render_events(result) -> None:
    events = tuple(
        event for event in result.events if event.kind not in {"campaign-started", "step-started"}
    )
    if not events:
        return

    table = Table(title="Campaign Orchestration Progress")
    table.add_column("Step", justify="right")
    table.add_column("Event")
    table.add_column("Stage")
    table.add_column("Action")
    table.add_column("Request ID")
    for event in events:
        table.add_row(
            str(event.step),
            event.kind,
            event.stage or "-",
            event.action or "-",
            event.request_id or "-",
        )
    console.print(table)


def _render_summary(result, provider: str | None) -> None:
    last = result.last_result
    title = (
        "Campaign Runtime Action"
        if result.policy == POLICY_ONCE
        else "Campaign Orchestration Summary"
    )
    table = Table(
        title=title,
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_row("Campaign ID", result.campaign_id)
    table.add_row("Provider", provider or "None configured")
    table.add_row("Policy", result.policy)
    table.add_row("Steps", str(result.steps))
    table.add_row("Completed", "Yes" if result.completed else "No")
    table.add_row("Paused", "Yes" if result.paused else "No")
    table.add_row("Uncertain", "Yes" if result.uncertain else "No")
    table.add_row("Stage", last.stage if last and last.stage else "Unknown")
    table.add_row("Action", last.action if last and last.action else "None")
    table.add_row("Request ID", last.request_id if last and last.request_id else "None")
    table.add_row("Warnings", str(len(result.warnings)))
    console.print(table)


def campaign_run_command(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Explicit execution provider. Use 'in-memory' for deterministic local execution.",
    ),
    once: bool = typer.Option(False, "--once", help="Advance exactly one safe action."),
    until_blocked: bool = typer.Option(
        False,
        "--until-blocked",
        help="Continue until completion, pause, uncertainty, error, or no progress.",
    ),
    until_complete: bool = typer.Option(
        False,
        "--until-complete",
        help="Continue toward completion within the configured step limit.",
    ),
    max_steps: int = typer.Option(
        100,
        "--max-steps",
        min=1,
        help="Maximum safe actions for a multi-step orchestration run.",
    ),
) -> None:
    """Run a campaign according to one bounded orchestration policy."""
    try:
        project = campaign_cli.Project.discover()
        adapters = _adapters_for(provider)
        policy = _policy_for(
            once=once,
            until_blocked=until_blocked,
            until_complete=until_complete,
        )
        orchestrator = CampaignOrchestratorAPI(_runner(project, adapters))
        result = PersistedCampaignOrchestratorAPI.for_project(project, orchestrator).run(
            campaign_id,
            policy=policy,
            max_steps=max_steps,
        )
    except (ConfigurationError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if not result.errors:
        _render_events(result)
        _render_summary(result, provider)

    for warning in result.warnings:
        console.print(f"[bold yellow]Warning:[/bold yellow] {warning}")
    for error in result.errors:
        console.print(f"[bold red]Error:[/bold red] {error}")

    if result.errors or result.uncertain:
        raise typer.Exit(code=1)
