"""Rich renderer for campaign fix rollback execution reports."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.campaign_fix_rollback_execution import CampaignFixRollbackExecutionReport


class CampaignFixRollbackExecutionRenderer:
    """Render rollback execution outcomes for terminal users."""

    def render(self, report: CampaignFixRollbackExecutionReport) -> Panel:
        """Return a Rich panel describing a rollback execution report."""
        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold")
        summary.add_column()
        summary.add_row("Campaign", report.campaign_name)
        summary.add_row("Mode", "Dry run" if report.dry_run else "Executed")
        summary.add_row("Removed", str(len(report.removed)))
        summary.add_row("Would remove", str(len(report.would_remove)))
        summary.add_row("Already missing", str(len(report.missing)))
        summary.add_row("Skipped", str(len(report.skipped)))

        results = Table(show_header=True, header_style="bold")
        results.add_column("Status")
        results.add_column("Operation")
        results.add_column("Target")
        results.add_column("Detail")

        for result in report.results:
            results.add_row(
                result.status,
                result.operation,
                result.target or "—",
                result.detail,
            )

        footer = Text(
            "Dry run completed; nothing was changed."
            if report.dry_run
            else "Rollback execution completed."
        )

        return Panel(
            Group(summary, Text(), results, Text(), footer),
            title="CreativeOS Campaign Rollback",
        )
