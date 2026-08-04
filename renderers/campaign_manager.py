"""Rich renderer for deterministic campaign manager decisions."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from api.campaign_manager import CampaignManagerResult


class CampaignManagerRenderer:
    """Render one campaign manager decision for the terminal."""

    def render(self, result: CampaignManagerResult) -> Panel:
        """Return a Rich panel containing today's campaign priority."""
        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", result.campaign)
        summary.add_row("Date", result.today.isoformat())
        summary.add_row("Phase", result.current_phase)
        summary.add_row("Priority Action", result.priority_action or "None")
        summary.add_row("Reason", result.reason or "None")
        summary.add_row("Next Milestone", result.next_milestone or "None")

        content = [summary]

        if result.task is not None:
            task = Table(title="Related Task", show_header=False, box=None, pad_edge=False)
            task.add_row("Request", result.task.request_id)
            task.add_row("Asset", result.task.asset_id)
            task.add_row("Media Type", result.task.media_type)
            task.add_row("Provider", result.task.provider)
            task.add_row("Scheduled", result.task.scheduled_for.isoformat())
            task.add_row("Status", result.task.status)
            task.add_row("Priority", str(result.task.priority))
            content.extend((Text(""), task))

        if result.warnings:
            content.extend((Text(""), Text("Warnings", style="bold yellow")))
            content.extend(Text(f"• {warning}") for warning in result.warnings)

        if result.errors:
            content.extend((Text(""), Text("Errors", style="bold red")))
            content.extend(Text(f"• {error}") for error in result.errors)

        return Panel(
            Group(*content),
            title="CreativeOS Campaign Today",
        )
