"""Rich renderer for campaign dashboard results."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from api.campaign_dashboard import CampaignDashboardResult


class CampaignDashboardRenderer:
    """Render a structured campaign dashboard result for the terminal."""

    def render(self, result: CampaignDashboardResult) -> Panel:
        """Return a Rich panel containing campaign overview details."""
        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", result.campaign)
        summary.add_row(
            "Readiness",
            f"{result.readiness_label} ({result.readiness_score})",
        )
        summary.add_row("Quality Score", str(result.quality_score))
        summary.add_row("Phase", result.current_phase)
        summary.add_row("Completion", f"{result.completion_percent}%")
        summary.add_row("Overdue Tasks", str(result.overdue_task_count))
        summary.add_row("Due Today", str(result.due_today_count))
        summary.add_row("Next Milestone", result.next_milestone or "None")
        summary.add_row("Recommendations", str(result.recommendation_count))
        summary.add_row("Warnings", str(result.warning_count))
        summary.add_row("Errors", str(result.error_count))

        content: list[object] = [summary]
        if result.warnings:
            content.extend(
                (
                    Text(""),
                    Text("Warnings", style="bold yellow"),
                    Text("\n".join(f"- {warning}" for warning in result.warnings)),
                )
            )
        if result.errors:
            content.extend(
                (
                    Text(""),
                    Text("Errors", style="bold red"),
                    Text("\n".join(f"- {error}" for error in result.errors)),
                )
            )

        return Panel(
            Group(*content),
            title="CreativeOS Campaign Dashboard",
        )
