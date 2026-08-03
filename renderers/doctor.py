"""Rich renderer for CreativeOS doctor reports."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.doctor import DoctorReport


class DoctorRenderer:
    """Render a doctor report for the terminal."""

    def render(self, report: DoctorReport) -> Panel:
        """Return a Rich panel containing the health report."""
        sections = []

        categories = dict.fromkeys(check.category for check in report.checks)

        for category in categories:
            table = Table(
                title=category,
                show_header=False,
                box=None,
                expand=True,
                padding=(0, 1),
            )
            table.add_column("Status", width=3)
            table.add_column("Check")
            table.add_column("Detail")

            for check in report.checks:
                if check.category != category:
                    continue

                if check.passed:
                    status = Text("✓", style="bold green")
                    name = Text(check.name, style="green")
                elif check.warning:
                    status = Text("!", style="bold yellow")
                    name = Text(check.name, style="yellow")
                else:
                    status = Text("✗", style="bold red")
                    name = Text(check.name, style="red")

                table.add_row(status, name, check.detail)

            sections.append(table)

        if report.failed_count:
            result = Text(
                (
                    f"Health checks failed — {report.failed_count} failed, "
                    f"{report.warning_count} warnings, {report.passed_count} passed. "
                    f"Health score: {report.health_score}%."
                ),
                style="bold red",
            )
            border_style = "red"
        elif report.warning_count:
            result = Text(
                (
                    f"System healthy with warnings — {report.warning_count} warnings, "
                    f"{report.passed_count} passed. Health score: "
                    f"{report.health_score}%."
                ),
                style="bold yellow",
            )
            border_style = "yellow"
        else:
            result = Text(
                (
                    f"System healthy — {report.passed_count} checks passed. "
                    f"Health score: {report.health_score}%."
                ),
                style="bold green",
            )
            border_style = "green"

        sections.append(result)

        return Panel(
            Group(*sections),
            title="CreativeOS Doctor",
            border_style=border_style,
        )
