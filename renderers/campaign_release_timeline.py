"""Rich renderer for deterministic campaign release timelines."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.campaign_release_timeline import CampaignReleaseTimeline


class CampaignReleaseTimelineRenderer:
    """Render a campaign release timeline for terminal presentation."""

    def render(self, campaign_name: str, timeline: CampaignReleaseTimeline) -> Panel:
        """Return a Rich panel containing campaign metadata and events."""
        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", campaign_name)
        summary.add_row("Release Date", timeline.release_date.isoformat())
        summary.add_row("Type", timeline.campaign_type)

        events = Table(pad_edge=False)
        events.add_column("Date")
        events.add_column("Day", justify="right")
        events.add_column("Category")
        events.add_column("Activity")

        for event in timeline.events:
            offset = str(event.day_offset)
            if event.day_offset > 0:
                offset = f"+{event.day_offset}"
            events.add_row(
                event.date.isoformat(),
                offset,
                event.category,
                event.title,
            )

        return Panel(
            Group(summary, Text(""), events),
            title="CreativeOS Campaign Timeline",
        )
