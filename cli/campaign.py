"""Campaign commands for CreativeOS."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai.manager import AIManager
from core.config import ConfigurationError
from core.project import Project
from services.campaign import CampaignService
from services.campaign_generator import CampaignGeneratorService
from services.campaign_run_state import CampaignRunStateError, JsonCampaignRunStore

app = typer.Typer(help="Create and manage music marketing campaigns.", no_args_is_help=True)
console = Console()
CAMPAIGN_RUNS_PATH = Path(".creativeos") / "runtime" / "campaign-runs"


@app.command("create")
def create_campaign(
    name: str = typer.Argument(..., help="Campaign or release name."),
    artist: str | None = typer.Option(None, "--artist", help="Override the configured artist."),
) -> None:
    """Create a complete campaign workspace."""
    try:
        project = Project.discover()
        path: Path = CampaignService(project).create(name, artist=artist)
    except (ConfigurationError, FileExistsError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Created campaign:[/bold green] {path}")


@app.command("generate")
def generate_campaign(
    name: str = typer.Argument(..., help="Campaign or release name."),
    force: bool = typer.Option(False, "--force", help="Replace existing campaign content."),
) -> None:
    """Generate marketing assets for an existing campaign."""
    try:
        project = Project.discover()
        provider = AIManager(project.config.ai).default()
        paths = CampaignGeneratorService(project, provider).generate(name, force=force)
    except (ConfigurationError, FileExistsError, FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Generated {len(paths)} campaign assets[/bold green] using {provider.name}."
    )
    for path in paths:
        console.print(f"- {path.relative_to(project.root)}")


@app.command("status")
def campaign_status(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
) -> None:
    """Display a persisted campaign run without advancing it."""
    try:
        project = Project.discover()
        run = JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH).load(campaign_id)
    except (ConfigurationError, CampaignRunStateError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    evidence = (
        "\n".join(
            f"{item.kind}: {item.reference_id} (recorded by {item.recorded_by})"
            for item in run.evidence
        )
        or "None recorded"
    )
    table = Table(
        title="Campaign Runtime Status",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_row("Campaign ID", run.campaign_id)
    table.add_row("Work ID", run.work_id)
    table.add_row("Work", run.plan.work_name)
    table.add_row("Stage", run.stage)
    table.add_row("Evidence", evidence)
    table.add_row("Next requirement", run.requires_action)
    console.print(table)
