"""CreativeOS command-line interface."""

import typer
from rich.console import Console
from rich.panel import Panel

from cli.song import app as song_app
from core.config import ConfigurationError
from core.project import Project

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
    except ConfigurationError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    output = f"""
[bold cyan]Workspace[/bold cyan]
{project.name}

[bold cyan]Artist[/bold cyan]
{project.artist}

[bold cyan]Current Song[/bold cyan]
{project.current_song}

[bold cyan]Upcoming Song[/bold cyan]
{project.upcoming_song}

[bold cyan]Active Campaigns[/bold cyan]
{len(project.active_campaigns)}
"""

    console.print(
        Panel.fit(
            output,
            title="CreativeOS v0.1",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
