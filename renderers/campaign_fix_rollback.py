"""Rich renderer for campaign fix rollback plans."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.campaign_fix_rollback import CampaignFixRollbackPlan


class CampaignFixRollbackRenderer:
    """Render a read-only campaign rollback plan."""

    def render(self, plan: CampaignFixRollbackPlan) -> Panel:
        """Return a Rich panel containing safe and skipped rollback actions."""
        summary = Table(show_header=False, box=None, pad_edge=False)
        summary.add_row("Campaign", plan.campaign_name)
        summary.add_row("Safe actions", str(len(plan.safe_actions)))
        summary.add_row("Skipped actions", str(len(plan.skipped_actions)))

        sections: list[object] = [summary]
        sections.extend(self._section("Safe Rollback Actions", plan.safe_actions))
        sections.extend(self._section("Skipped Rollback Actions", plan.skipped_actions))

        if not plan.actions:
            sections.append(Text("No rollback actions are available.", style="bold green"))
        else:
            sections.append(
                Text(
                    "Nothing has been changed. This command displays a plan only.",
                    style="bold yellow",
                )
            )

        return Panel(
            Group(*sections),
            title="CreativeOS Campaign Rollback Plan",
            border_style="yellow" if plan.actions else "green",
        )

    @staticmethod
    def _section(title: str, actions: tuple) -> list[object]:
        if not actions:
            return []

        table = Table(title=f"{title} ({len(actions)})", pad_edge=False)
        table.add_column("Operation")
        table.add_column("Source")
        table.add_column("Target")
        table.add_column("Detail")
        for action in actions:
            table.add_row(
                action.operation,
                action.source_check,
                action.target or "None",
                action.detail,
            )
        return [table]
