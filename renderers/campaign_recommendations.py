"""Rich renderer for deterministic campaign recommendations."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.campaign_recommendation import CampaignRecommendations


class CampaignRecommendationsRenderer:
    """Render campaign recommendations for the terminal."""

    def render(self, recommendations: CampaignRecommendations) -> Panel:
        """Return a Rich panel containing campaign recommendations."""
        summary = Table(
            show_header=False,
            box=None,
            pad_edge=False,
        )
        summary.add_row("Campaign", recommendations.campaign_name)
        summary.add_row(
            "Recommendations",
            str(len(recommendations.items)),
        )
        summary.add_row(
            "High impact",
            str(recommendations.high_impact_count),
        )
        summary.add_row(
            "Actionable",
            str(recommendations.actionable_count),
        )

        sections: list[object] = [summary]

        if recommendations.items:
            table = Table(
                title="Recommendations",
                pad_edge=False,
            )
            table.add_column("Priority", justify="right")
            table.add_column("Impact")
            table.add_column("Source")
            table.add_column("Recommendation")
            table.add_column("Action")

            for item in recommendations.items:
                table.add_row(
                    str(item.priority),
                    item.impact.title(),
                    f"{item.category}: {item.source_check}",
                    f"{item.title}\n{item.detail}",
                    item.action or "No action provided",
                )

            sections.append(table)
            sections.append(
                Text(
                    "Review the highest-priority recommendations first.",
                    style="bold yellow",
                )
            )
            border_style = "yellow"
        else:
            sections.append(
                Text(
                    "No campaign recommendations.",
                    style="bold green",
                )
            )
            border_style = "green"

        return Panel(
            Group(*sections),
            title="CreativeOS Campaign Recommendations",
            border_style=border_style,
        )
