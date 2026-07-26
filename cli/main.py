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
from services.campaign_planner import CampaignPlannerService
from services.daily_recommendation import DailyRecommendationService
from services.doctor import DoctorService
from services.workspace_summary import WorkspaceSummaryService
from story import NarrativeTimelineService, StoryContextService

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


@app.command("next")
def next_recommendation(
    work_id: str = typer.Argument(..., help="Stable Creative Universe work ID."),
    week: int = typer.Option(..., "--week", min=1, help="Current one-based campaign week."),
    weeks: int = typer.Option(..., "--weeks", min=1, help="Total campaign length in weeks."),
    objective: str = typer.Option(..., "--objective", help="Primary campaign objective."),
    audience: str = typer.Option(..., "--audience", help="Target audience."),
    tone: str = typer.Option(..., "--tone", help="Creative tone."),
    platform: list[str] = typer.Option(  # noqa: B008
        ..., "--platform", help="Target platform; repeat as needed."
    ),
    arc_id: str | None = typer.Option(
        None, "--arc", help="Story arc ID when more than one exists."
    ),
) -> None:
    """Recommend the active content direction for a campaign week."""
    try:
        project = Project.discover()
        context = StoryContextService(project).build(work_id)
        timeline = NarrativeTimelineService().build(
            context, weeks=weeks, arc_id=arc_id
        )
        plan = CampaignPlannerService().build(
            context,
            timeline,
            objective=objective,
            audience=audience,
            tone=tone,
            platforms=tuple(platform),
        )
        recommendation = DailyRecommendationService().recommend(plan, week=week)
    except (ConfigurationError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(recommendation.render())


if __name__ == "__main__":
    app()
