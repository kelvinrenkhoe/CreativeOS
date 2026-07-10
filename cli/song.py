"""Song commands for the CreativeOS CLI."""

import typer
from rich.console import Console

from core.config import ConfigurationError, find_workspace
from services.song import SongError, SongService

app = typer.Typer(
    help="Create and manage song workspaces.",
    no_args_is_help=True,
)

console = Console()


@app.command("new")
def create_song(name: str) -> None:
    """
    Create a new song workspace.

    Example:
        creativeos song new "My New Song"
    """
    try:
        workspace = find_workspace()
        song = SongService().create(name=name, workspace=workspace)

    except (ConfigurationError, SongError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Song workspace created successfully.[/bold green]\n"
        f"[bold]Name:[/bold] {song.name}\n"
        f"[bold]Path:[/bold] {song.path}"
    )
