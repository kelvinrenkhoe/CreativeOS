"""CreativeOS command-line interface."""

import platform
from importlib.metadata import PackageNotFoundError, version

import typer
from rich.console import Console
from rich.table import Table

from cli.ai import app as ai_app
from cli.campaign import app as campaign_app
from cli.index import app as index_app
from cli.repository import search_command, stats_command
from cli.song import app as song_app
from core.config import ConfigurationError
from core.project import Project
from renderers.doctor import DoctorRenderer
from renderers.status import StatusRenderer
from services.doctor import DoctorService
from services.workspace_summary import WorkspaceSummaryService

app = typer.Typer(
    help="CreativeOS - Productivity toolkit for creators.",
    no_args_is_help=True,
)

app.add_typer(song_app, name="song")
app.add_typer(campaign_app, name="campaign")
app.add_typer(index_app, name="index")
app.add_typer(ai_app, name="ai")
app.command("search")(search_command)
app.command("stats")(stats_command)

console = Console()


@app.callback()
def main() -> None:
    """CreativeOS command-line interface."""


@app.command("version")
def version_command() -> None:
    """Display CreativeOS version information."""
    try:
        creativeos_version = version("creativeos")
    except PackageNotFoundError:
        creativeos_version = "development"

    table = Table(
        title="CreativeOS Version",
        show_header=False,
        box=None,
        pad_edge=False,
    )

    table.add_row("CreativeOS", creativeos_version)
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.platform())

    console.print(table)


@app.command()
def doctor() -> None:
    """Check the CreativeOS installation and project health."""
    report = DoctorService().run()
    panel = DoctorRenderer().render(report)

    console.print(panel)

    if not report.healthy:
        raise typer.Exit(code=1)


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
