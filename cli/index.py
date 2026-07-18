"""Repository index CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from core.project import Project
from services.index import IndexError, IndexService

app = typer.Typer(
    help="Build and inspect the repository index.",
    no_args_is_help=True,
)
console = Console()


def _service() -> tuple[Project, IndexService]:
    project = Project.discover()
    return project, IndexService(project)


def _print_stats(title: str, project: Project, service: IndexService) -> None:
    index = service.load()
    table = Table(title=title, show_header=False, box=None, pad_edge=False)
    table.add_row("Workspace", project.name)
    table.add_row("Songs", str(index.stats.songs))
    table.add_row("Campaigns", str(index.stats.campaigns))
    table.add_row("Books", str(index.stats.books))
    table.add_row("Assets", str(index.stats.assets))
    table.add_row("Indexed", index.generated_at.isoformat())
    console.print(table)


@app.command("build")
def build_index() -> None:
    """Build and persist the repository index."""
    project, service = _service()
    service.refresh()
    _print_stats("Repository Index Built", project, service)
    console.print(f"[green]Written to {service.index_path}[/green]")


@app.command("refresh")
def refresh_index() -> None:
    """Rebuild and replace the repository index."""
    project, service = _service()
    service.refresh()
    _print_stats("Repository Index Refreshed", project, service)


@app.command("validate")
def validate_index() -> None:
    """Validate the saved repository index."""
    try:
        project, service = _service()
        service.validate()
    except IndexError as error:
        console.print(f"[bold red]Invalid repository index:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Repository index is healthy for {project.name}.[/green]")
