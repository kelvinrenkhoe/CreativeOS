"""Rich renderer for campaign fix execution reports."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.campaign_fix_execution import CampaignFixExecutionReport


class CampaignFixExecutionRenderer:
    """Render safe campaign fix execution results."""

    def render(self, report: CampaignFixExecutionReport) -> Panel:
        """Return a Rich panel summarising applied and skipped fixes."""
        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", report.campaign_name)
        summary.add_row("Applied", str(len(report.applied)))
        summary.add_row("Already present", str(len(report.already_present)))
        summary.add_row("Skipped", str(len(report.skipped)))

        sections: list[object] = [summary]
        sections.extend(self._section("Applied", report.applied, "green", "✓"))
        sections.extend(
            self._section(
                "Already Present",
                report.already_present,
                "cyan",
                "○",
            )
        )
        sections.extend(self._section("Skipped", report.skipped, "yellow", "•"))

        if not report.results:
            sections.append(Text("No fixes were required.", style="bold green"))

        return Panel(
            Group(*sections),
            title="CreativeOS Campaign Fix",
            border_style="green" if not report.skipped else "yellow",
        )

    @staticmethod
    def _section(
        title: str,
        results: tuple,
        style: str,
        marker: str,
    ) -> list[object]:
        if not results:
            return []

        table = Table(title=f"{title} ({len(results)})", pad_edge=False)
        table.add_column("Result")
        table.add_column("Target")
        table.add_column("Detail")
        for result in results:
            table.add_row(
                f"{marker} {result.source_check}",
                result.target or "None",
                result.detail,
            )
        return [table]
