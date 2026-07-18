"""Status renderer for CreativeOS."""

from models.workspace_summary import WorkspaceSummary
from rich.panel import Panel


class StatusRenderer:
    """Render a workspace summary as a Rich panel."""

    def render(self, summary: WorkspaceSummary) -> Panel:
        body = f"""
[bold cyan]Workspace[/bold cyan]
{summary.project_name}

[bold cyan]Artist[/bold cyan]
{summary.artist_name}

[bold cyan]Current Song[/bold cyan]
{summary.current_song}

[bold cyan]Upcoming Song[/bold cyan]
{summary.upcoming_song}

[bold cyan]Active Campaigns[/bold cyan]
{summary.active_campaigns}
"""

        return Panel.fit(
            body.strip(),
            title="CreativeOS v0.3",
            border_style="green",
        )
