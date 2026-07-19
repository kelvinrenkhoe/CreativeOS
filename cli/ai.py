"""AI provider commands for CreativeOS."""

import typer
from rich.console import Console
from rich.table import Table

from ai.exceptions import AIError
from ai.manager import AIManager
from core.config import ConfigurationError
from core.project import Project

app = typer.Typer(help="Inspect and test CreativeOS AI providers.", no_args_is_help=True)
console = Console()


def _manager() -> AIManager:
    project = Project.discover()
    return AIManager(project.config.ai)


@app.command("providers")
def providers_command() -> None:
    """List available AI providers."""
    manager = AIManager()
    table = Table(title="Available AI Providers")
    table.add_column("Provider")
    for name in manager.available():
        table.add_row(name)
    console.print(table)


@app.command("provider")
def provider_command() -> None:
    """Show the active AI provider and model."""
    try:
        provider = _manager().default()
    except (ConfigurationError, AIError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Active AI Provider", show_header=False, box=None)
    table.add_row("Provider", provider.name)
    table.add_row("Model", provider.model or "default")
    console.print(table)


@app.command("test")
def test_command() -> None:
    """Send a test prompt to the active provider."""
    prompt = "Hello CreativeOS"
    try:
        provider = _manager().default()
        response = provider.generate(prompt)
    except (ConfigurationError, AIError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]Provider:[/bold] {provider.name}")
    console.print(f"[bold]Model:[/bold] {provider.model or 'default'}")
    console.print(f"\n[bold]Prompt:[/bold]\n{prompt}")
    console.print(f"\n[bold]Response:[/bold]\n{response}")
