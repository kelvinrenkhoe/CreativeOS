"""Rich renderer for deterministic campaign release timelines."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from api.campaign_timeline import CampaignTimelineResult


class CampaignReleaseTimelineRenderer:
    """Render a structured campaign timeline result for the terminal."""

    def render(self, result: CampaignTimelineResult) -> Panel:
        """Return a Rich panel containing campaign metadata and events."""
        if result.release_date is None:
            raise ValueError("timeline result has no release date")

        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", result.campaign)
        summary.add_row("Release Date", result.release_date.isoformat())
        summary.add_row("Type", result.campaign_type)

        events = Table(pad_edge=False)
        events.add_column("Date")
        events.add_column("Day", justify="right")
        events.add_column("Category")
        events.add_column("Activity")

        for event in result.timeline_events:
            offset = str(event.day_offset)
            if event.day_offset > 0:
                offset = f"+{event.day_offset}"
            events.add_row(
                event.date.isoformat(),
                offset,
                event.category,
                event.title,
            )

        content = [summary, Text(""), events]
        if result.warnings:
            content.extend((Text(""), Text("\n".join(result.warnings))))

        return Panel(
            Group(*content),
            title="CreativeOS Campaign Timeline",
        )
