"""CreativeOS command-line interface."""

import typer
from rich.console import Console

from cli.song import app as song_app
from core.config import ConfigurationError
from core.project import Project
from renderers.status import StatusRenderer
from services.workspace_summary import WorkspaceSummaryService


app = typer.Typer(
    help="CreativeOS - Productivity toolkit for creators.",
    no_args_is_help=True,
)

app.add_typer(song_app, name="song")

console = Console()


@app.callback()
def main() -> None:
    """CreativeOS command-line interface."""


@app.command()
def status() -> None:
    """Display the current CreativeOS workspace status."""
    try:
        project = Project()
        summary = WorkspaceSummaryService(project).load()
        panel = StatusRenderer().render(summary)

    except ConfigurationError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(panel)


if __name__ == "__main__":
    app()