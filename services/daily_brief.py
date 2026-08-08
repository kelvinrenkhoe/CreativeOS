"""Daily execution brief composition for CreativeOS campaigns."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from models.action import Action
from models.campaign_context import CampaignContext
from services.action_repository import ActionRepository
from services.action_service import ActionProgress, ActionService
from services.campaign_context import CampaignContextService
from services.execution_planner import ExecutionPlanner


@dataclass(frozen=True, slots=True)
class MilestoneStatus:
    """One campaign milestone relative to the Daily Brief date."""

    name: str
    milestone_date: date
    days_from_brief: int

    @property
    def is_today(self) -> bool:
        return self.days_from_brief == 0

    @property
    def is_overdue(self) -> bool:
        return self.days_from_brief < 0

    @property
    def urgency(self) -> str:
        if self.is_overdue:
            return "overdue"
        if self.is_today:
            return "today"
        if self.days_from_brief <= 3:
            return "imminent"
        if self.days_from_brief <= 7:
            return "upcoming"
        return "later"


@dataclass(frozen=True, slots=True)
class MilestoneProgress:
    """Read-only action progress for one campaign milestone."""

    name: str
    total: int
    completed: int
    ready: int
    pending: int
    blocked: int

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.completed / self.total) * 100, 1)


@dataclass(frozen=True, slots=True)
class DailyBrief:
    """Read-only daily execution summary for one campaign."""

    organization_id: str
    project_id: str
    campaign: CampaignContext
    brief_date: date
    today: tuple[Action, ...]
    overdue: tuple[Action, ...]
    blocked: tuple[Action, ...]
    ready: tuple[Action, ...]
    next_actions: tuple[Action, ...]
    milestones: tuple[MilestoneStatus, ...]
    milestone_progress: tuple[MilestoneProgress, ...]
    progress: ActionProgress

    @property
    def recommended_next(self) -> Action | None:
        return self.next_actions[0] if self.next_actions else None

    @property
    def focus_milestone(self) -> MilestoneStatus | None:
        current_or_future = tuple(
            milestone for milestone in self.milestones if milestone.days_from_brief >= 0
        )
        if current_or_future:
            return current_or_future[0]
        return self.milestones[-1] if self.milestones else None

    @property
    def focus_milestone_actions(self) -> tuple[Action, ...]:
        """Return ready actions explicitly linked to the focused milestone."""
        focus = self.focus_milestone
        if focus is None:
            return ()
        return tuple(action for action in self.ready if action.milestone == focus.name)


class DailyBriefService:
    """Compose campaign context and execution state into one daily brief."""

    def __init__(
        self,
        repository_root: Path,
        organization_id: str,
        project_id: str,
        campaign_id: str,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.organization_id = organization_id
        self.project_id = project_id
        self.campaign_service = CampaignContextService(
            self.repository_root,
            organization_id,
            project_id,
        )
        self.campaign = self.campaign_service.load(campaign_id)
        repository = ActionRepository(
            self.repository_root,
            organization_id,
            project_id,
            campaign_id,
        )
        self.planner = ExecutionPlanner(ActionService(repository))

    def build(self, on_date: date | None = None, *, next_limit: int = 3) -> DailyBrief:
        target = on_date or date.today()
        plan = self.planner.plan(target)
        next_actions = self.planner.next(target, limit=next_limit)
        milestones = tuple(
            sorted(
                (
                    MilestoneStatus(
                        name=name,
                        milestone_date=milestone_date,
                        days_from_brief=(milestone_date - target).days,
                    )
                    for name, milestone_date in self.campaign.milestones
                ),
                key=lambda item: (item.milestone_date, item.name),
            )
        )
        milestone_progress = self._milestone_progress(milestones, plan.ready)
        return DailyBrief(
            organization_id=self.organization_id,
            project_id=self.project_id,
            campaign=self.campaign,
            brief_date=target,
            today=plan.today,
            overdue=plan.overdue,
            blocked=plan.blocked,
            ready=plan.ready,
            next_actions=next_actions,
            milestones=milestones,
            milestone_progress=milestone_progress,
            progress=plan.progress,
        )

    def _milestone_progress(
        self,
        milestones: tuple[MilestoneStatus, ...],
        ready_actions: tuple[Action, ...],
    ) -> tuple[MilestoneProgress, ...]:
        actions = tuple(
            action
            for action in self.planner.action_service.repository.list()
            if action.status != "cancelled"
        )
        ready_ids = {action.action_id for action in ready_actions}
        summaries: list[MilestoneProgress] = []

        for milestone in milestones:
            linked = tuple(action for action in actions if action.milestone == milestone.name)
            completed = sum(action.status == "completed" for action in linked)
            blocked = sum(action.status == "blocked" for action in linked)
            ready = sum(action.action_id in ready_ids for action in linked)
            pending = len(linked) - completed - blocked - ready
            summaries.append(
                MilestoneProgress(
                    name=milestone.name,
                    total=len(linked),
                    completed=completed,
                    ready=ready,
                    pending=pending,
                    blocked=blocked,
                )
            )

        return tuple(summaries)
