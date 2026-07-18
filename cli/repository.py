"""Repository query CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from core.project import Project
from services.repository import RepositoryError

console = Console()


def search_command(
    query: str = typer.Argument(..., help="Text to search for."),
    entity_type: str | None = typer.Option(
        None,
        "--type",
        help="Limit results to song, campaign, book, or asset.",
    ),
) -> None:
    """Search indexed repository content."""
    project = Project.discover()
    try:
        results = project.search(query, entity_type=entity_type)
    except RepositoryError as error:
        console.print(f"[bold red]Search failed:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    if not results:
        console.print(f"No repository entries matched [bold]{query}[/bold].")
        return

    table = Table(title=f"Search results for {query}")
    table.add_column("Type")
    table.add_column("Name")
    table.add_column("Path")
    for entity in results:
        table.add_row(entity.__class__.__name__.lower(), entity.name, str(entity.path))
    console.print(table)


def stats_command() -> None:
    """Display indexed repository statistics."""
    project = Project.discover()
    stats = project.stats()

    table = Table(title="CreativeOS Repository", show_header=False, box=None, pad_edge=False)
    table.add_row("Workspace", project.name)
    table.add_row("Songs", str(stats.songs))
    table.add_row("Campaigns", str(stats.campaigns))
    table.add_row("Books", str(stats.books))
    table.add_row("Assets", str(stats.assets))
    table.add_row("Total", str(stats.total))
    console.print(table)
