"""Rich renderer for deterministic campaign plans."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from api.campaign_planner import CampaignPlanResult


class CampaignPlannerRenderer:
    """Render a multi-day campaign plan for the terminal."""

    def render(self, result: CampaignPlanResult) -> Panel:
        """Return a Rich panel containing the campaign plan."""
        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", result.campaign)
        summary.add_row("Start", result.start.isoformat())
        summary.add_row("End", result.end.isoformat())
        summary.add_row("Days", str(len(result.daily_plans)))

        content = [summary]

        for daily in result.daily_plans:
            day = Table(
                title=daily.date.strftime("%A, %d %B %Y"),
                show_header=True,
                header_style="bold",
                box=None,
                pad_edge=False,
            )
            day.add_column("Item")
            day.add_column("Details")
            day.add_row("Priority", daily.priority)
            day.add_row("Estimated effort", f"{daily.estimated_minutes} minutes")
            day.add_row("Milestone", daily.milestone or "None")

            if daily.tasks:
                for task in daily.tasks:
                    details = (
                        f"{task.media_type} · priority {task.priority} · "
                        f"{task.scheduled_for.isoformat()}"
                    )
                    day.add_row(task.asset_id, details)
            else:
                day.add_row("Tasks", "None")

            content.extend((Text(""), day))

        if result.warnings:
            content.extend((Text(""), Text("Warnings", style="bold yellow")))
            content.extend(Text(f"• {warning}") for warning in result.warnings)

        if result.errors:
            content.extend((Text(""), Text("Errors", style="bold red")))
            content.extend(Text(f"• {error}") for error in result.errors)

        return Panel(
            Group(*content),
            title="CreativeOS Campaign Plan",
        )
