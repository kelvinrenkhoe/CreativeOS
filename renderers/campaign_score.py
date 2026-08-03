"""Rich renderer for deterministic campaign scores."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.campaign_score import CampaignScore


class CampaignScoreRenderer:
    """Render campaign quality scores for the terminal."""

    def render(self, score: CampaignScore) -> Panel:
        """Return a Rich panel containing campaign score details."""
        summary = Table(
            show_header=False,
            box=None,
            pad_edge=False,
        )
        summary.add_row("Campaign", score.campaign_name)
        summary.add_row("Overall score", f"{score.overall_score}%")

        categories = Table(
            title="Categories",
            pad_edge=False,
        )
        categories.add_column("Category")
        categories.add_column("Score", justify="right")
        categories.add_column("Checks", justify="right")

        for category in score.categories:
            categories.add_row(
                category.name,
                f"{category.score}%",
                f"{category.passed_checks}/{category.total_checks}",
            )

        findings = Table(
            title="Findings",
            show_header=False,
            box=None,
            pad_edge=False,
        )
        findings.add_column("Finding")

        finding_count = 0
        for category in score.categories:
            for finding in category.findings:
                findings.add_row(f"{category.name}: {finding}")
                finding_count += 1

        if finding_count == 0:
            findings.add_row("No campaign quality findings.")

        if score.overall_score >= 80:
            border_style = "green"
            result = Text("Campaign quality is strong.", style="bold green")
        elif score.overall_score >= 60:
            border_style = "yellow"
            result = Text(
                "Campaign quality needs improvement.",
                style="bold yellow",
            )
        else:
            border_style = "red"
            result = Text(
                "Campaign quality requires significant improvement.",
                style="bold red",
            )

        return Panel(
            Group(summary, categories, findings, result),
            title="CreativeOS Campaign Score",
            border_style=border_style,
        )
