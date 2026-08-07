"""CreativeOS command-line interface."""

import platform
from importlib.metadata import PackageNotFoundError, version

import typer
from rich.console import Console
from rich.table import Table

from cli.ai import app as ai_app
from cli.campaign import app as campaign_app
from cli.campaign_checkpoint import app as campaign_checkpoint_app
from cli.campaign_fix import fix_command
from cli.campaign_fix_rollback import rollback_plan_command
from cli.campaign_fix_rollback_execute import rollback_command
from cli.campaign_history import campaign_history_command
from cli.campaign_plan import campaign_plan_command
from cli.campaign_run import campaign_run_command
from cli.daily_brief import today_command
from cli.execution import app as execution_app
from cli.index import app as index_app
from cli.organization import app as organization_app
from cli.repository import search_command, stats_command
from cli.song import app as song_app
from cli.week_plan import app as week_plan_app
from cli.worker import app as worker_app
from core.config import ConfigurationError
from core.project import Project
from orchestrator import (
    CampaignRuntimePreset,
    CampaignRuntimePresetRegistry,
    RuntimeStage,
)
from renderers.doctor import DoctorRenderer
from renderers.status import StatusRenderer
from services.campaign_doctor import CampaignDoctorService
from services.campaign_planner import CampaignPlannerService
from services.daily_recommendation import DailyRecommendationService
from services.doctor import DoctorService
from services.workspace_summary import WorkspaceSummaryService
from story import NarrativeTimelineService, StoryContextService

app = typer.Typer(
    help="CreativeOS - Productivity toolkit for creators.",
    no_args_is_help=True,
)

campaign_app.registered_commands = [
    command for command in campaign_app.registered_commands if command.name != "run"
]
campaign_app.command("run")(campaign_run_command)
campaign_app.command("ai-plan")(campaign_plan_command)
campaign_app.command("history")(campaign_history_command)
campaign_app.add_typer(campaign_checkpoint_app, name="checkpoint")
campaign_app.add_typer(week_plan_app, name="week")
campaign_app.command("fix")(fix_command)
campaign_app.command("rollback-plan")(rollback_plan_command)
campaign_app.command("rollback")(rollback_command)
app.add_typer(song_app, name="song")
app.add_typer(campaign_app, name="campaign")
app.add_typer(worker_app, name="worker")
app.add_typer(index_app, name="index")
app.add_typer(ai_app, name="ai")
app.add_typer(organization_app, name="org")
app.add_typer(execution_app, name="execution")
app.command("today")(today_command)
app.command("search")(search_command)
app.command("stats")(stats_command)

console = Console()


def _campaign_preset_registry() -> CampaignRuntimePresetRegistry:
    """Return the built-in preset metadata required by Campaign Doctor."""
    registry = CampaignRuntimePresetRegistry()
    registry.register(
        CampaignRuntimePreset(
            name="music-release",
            description="Validate a music-release campaign before execution.",
            required_context_keys=("campaign",),
            stages=(
                RuntimeStage(
                    "brief",
                    lambda campaign: campaign,
                    ("campaign",),
                    "brief",
                ),
            ),
        )
    )
    return registry


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
def doctor(
    campaign: str | None = typer.Option(
        None,
        "--campaign",
        help="Check a named campaign instead of the workspace.",
    ),
    preset: str = typer.Option(
        "music-release",
        "--preset",
        help="Runtime preset used for campaign readiness checks.",
    ),
) -> None:
    """Check CreativeOS workspace or campaign health."""
    try:
        if campaign is None:
            report = DoctorService().run()
        else:
            project = Project.discover()
            report = CampaignDoctorService(
                project,
                _campaign_preset_registry(),
            ).diagnose(
                campaign,
                preset_name=preset,
                context={"campaign": campaign},
            )
    except (ConfigurationError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

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
        timeline = NarrativeTimelineService().build(context, weeks=weeks, arc_id=arc_id)
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
