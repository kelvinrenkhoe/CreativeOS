"""Weekly campaign content planning commands."""

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from core.config import ConfigurationError
from core.project import Project
from services.weekly_content_plan import (
    ContentCandidate,
    JsonWeeklyContentPlanStore,
    WeeklyContentPlan,
    WeeklyContentPlanError,
    WeeklyContentPlanner,
)

app = typer.Typer(help="Plan and inspect campaign content weeks.", no_args_is_help=True)
console = Console()
CONTENT_PLANS_PATH = Path(".creativeos") / "content-plans"

DEFAULT_CANDIDATES = (
    ContentCandidate(
        "instagram",
        "video-performance",
        "performance moment",
        "show the energy of the song",
        "Stream the song",
    ),
    ContentCandidate(
        "tiktok",
        "video-story",
        "behind the song",
        "explain the personal story",
        "Share your reaction",
    ),
    ContentCandidate(
        "facebook",
        "photo",
        "artist reflection",
        "connect the release to the artist journey",
        "Listen and share",
    ),
    ContentCandidate(
        "instagram",
        "lyric-card",
        "lyric meaning",
        "highlight one memorable line",
        "Save this lyric",
    ),
    ContentCandidate(
        "youtube",
        "video-cinematic",
        "cinematic scene",
        "translate the song emotion into a visual moment",
        "Watch the full story",
    ),
    ContentCandidate(
        "tiktok",
        "video-community",
        "audience response",
        "invite listeners into the campaign",
        "Use the sound",
    ),
    ContentCandidate(
        "facebook",
        "video-studio",
        "studio process",
        "show how the release was created",
        "Tell us what stands out",
    ),
    ContentCandidate(
        "instagram",
        "photo",
        "release artwork",
        "focus on the visual identity",
        "Add it to your playlist",
    ),
    ContentCandidate(
        "youtube",
        "video-reflection",
        "weekly reflection",
        "close the week with gratitude and direction",
        "Subscribe for the next chapter",
    ),
    ContentCandidate(
        "tiktok",
        "lyric-card",
        "listener prompt",
        "ask what the song means to the audience",
        "Comment your favourite line",
    ),
)


def _parse_week_start(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise WeeklyContentPlanError("week start must use YYYY-MM-DD") from exc
    if parsed.weekday() != 0:
        raise WeeklyContentPlanError("week start must be a Monday")
    return parsed


def _select_plan(
    store: JsonWeeklyContentPlanStore,
    campaign_id: str,
    week_start: date,
    *,
    replace: bool,
) -> tuple[WeeklyContentPlan, bool]:
    history = store.load()
    existing = next((plan for plan in history if plan.week_start == week_start), None)
    if existing is not None and not replace:
        return existing, False

    plan = WeeklyContentPlanner().build(
        campaign_id,
        week_start,
        DEFAULT_CANDIDATES,
        history=history,
    )
    store.save(plan, replace=replace)
    return plan, True


@app.command("plan")
def plan_week(
    campaign_id: str = typer.Argument(..., help="Stable campaign ID."),
    week_start: str = typer.Option(
        ...,
        "--week-start",
        help="Monday starting the planned week, formatted as YYYY-MM-DD.",
    ),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Explicitly replace an existing plan for the same week.",
    ),
) -> None:
    """Build or load one durable seven-day campaign content plan."""
    try:
        project = Project.discover()
        start = _parse_week_start(week_start)
        store = JsonWeeklyContentPlanStore(
            project.root / CONTENT_PLANS_PATH / f"{campaign_id}.json",
            campaign_id,
        )
        plan, created = _select_plan(
            store,
            campaign_id,
            start,
            replace=replace,
        )
    except (
        ConfigurationError,
        PermissionError,
        WeeklyContentPlanError,
        OSError,
        ValueError,
    ) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Weekly Content Plan · {campaign_id}", pad_edge=False)
    table.add_column("Date")
    table.add_column("Platform")
    table.add_column("Format")
    table.add_column("Concept")
    table.add_column("Angle")
    table.add_column("CTA")
    table.add_column("Status")
    for item in plan.items:
        table.add_row(
            item.scheduled_date.isoformat(),
            item.platform,
            item.format,
            item.concept,
            item.angle,
            item.call_to_action,
            item.status,
        )
    console.print(table)
    state = "Created" if created else "Loaded"
    console.print(f"[bold green]{state}:[/bold green] week of {plan.week_start.isoformat()}")
