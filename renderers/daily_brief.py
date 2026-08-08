"""Rich renderer for CreativeOS daily execution briefs."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models.action import Action
from services.daily_brief import DailyBrief, MilestoneStatus


class DailyBriefRenderer:
    """Render a compact daily execution brief."""

    def render(self, brief: DailyBrief) -> Panel:
        sections = [
            Text(
                f"{brief.organization_id} / {brief.project_id} / {brief.campaign.name}\n"
                f"{brief.brief_date.isoformat()}  •  status: {brief.campaign.status}"
            ),
            self._milestone_focus(brief.focus_milestone),
            self._milestone_table(brief.milestones),
            self._action_table("Today's Focus", brief.next_actions),
            self._action_table("Due Today", brief.today),
            self._action_table("Overdue", brief.overdue),
            self._action_table("Blocked", brief.blocked),
            Text(
                f"Progress: {brief.progress.completed}/{brief.progress.total} "
                f"({brief.progress.percent:.1f}%)"
            ),
        ]

        if brief.recommended_next is None:
            sections.append(Text("Recommended Next Step: No ready action."))
        else:
            sections.append(Text(f"Recommended Next Step: {brief.recommended_next.title}"))

        return Panel(Group(*sections), title="CreativeOS Daily Brief")

    @staticmethod
    def _milestone_focus(milestone: MilestoneStatus | None) -> Text:
        if milestone is None:
            return Text("Milestone Focus: No campaign milestone configured.")

        label = milestone.name.replace("_", " ").title()
        if milestone.is_today:
            timing = "today"
        elif milestone.is_overdue:
            days = abs(milestone.days_from_brief)
            timing = f"{days} day{'s' if days != 1 else ''} overdue"
        else:
            days = milestone.days_from_brief
            timing = f"in {days} day{'s' if days != 1 else ''}"

        return Text(f"Milestone Focus: {label} — {timing} [{milestone.urgency}]")

    @staticmethod
    def _milestone_table(milestones: tuple[MilestoneStatus, ...]) -> Table:
        table = Table(title="Campaign Milestones")
        table.add_column("Milestone")
        table.add_column("Date")
        table.add_column("Timing")
        table.add_column("Urgency")

        for milestone in milestones:
            if milestone.is_today:
                timing = "Today"
            elif milestone.is_overdue:
                days = abs(milestone.days_from_brief)
                timing = f"{days} day{'s' if days != 1 else ''} ago"
            else:
                days = milestone.days_from_brief
                timing = f"in {days} day{'s' if days != 1 else ''}"
            table.add_row(
                milestone.name.replace("_", " ").title(),
                milestone.milestone_date.isoformat(),
                timing,
                milestone.urgency,
            )

        if not milestones:
            table.add_row("-", "-", "None", "-")
        return table

    @staticmethod
    def _action_table(title: str, actions: tuple[Action, ...]) -> Table:
        table = Table(title=title)
        table.add_column("ID")
        table.add_column("Action")
        table.add_column("Priority")
        table.add_column("Due")

        for action in actions:
            table.add_row(
                action.action_id,
                action.title,
                action.priority,
                action.due_date.isoformat() if action.due_date else "-",
            )

        if not actions:
            table.add_row("-", "None", "-", "-")
        return table
