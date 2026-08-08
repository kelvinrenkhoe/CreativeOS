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
class MilestoneHealth:
    """Deterministic milestone health derived from deadline and progress."""

    name: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class MilestoneAttention:
    """Concise explanation of milestone work that needs intervention."""

    name: str
    status: str
    reason: str
    days_from_brief: int
    completed: int
    total: int
    pending: int
    blocked: int


@dataclass(frozen=True, slots=True)
class MilestoneIntervention:
    """Advisory intervention derived from milestone attention state."""

    name: str
    status: str
    suggestion: str


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
    milestone_health: tuple[MilestoneHealth, ...]
    milestone_attention: tuple[MilestoneAttention, ...]
    milestone_interventions: tuple[MilestoneIntervention, ...]
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

    @property
    def focus_milestone_health(self) -> MilestoneHealth | None:
        focus = self.focus_milestone
        if focus is None:
            return None
        return next((item for item in self.milestone_health if item.name == focus.name), None)


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
        milestone_health = self._milestone_health(milestones, milestone_progress)
        milestone_attention = self._milestone_attention(
            milestones,
            milestone_progress,
            milestone_health,
        )
        milestone_interventions = self._milestone_interventions(milestone_attention)
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
            milestone_health=milestone_health,
            milestone_attention=milestone_attention,
            milestone_interventions=milestone_interventions,
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

    @staticmethod
    def _milestone_health(
        milestones: tuple[MilestoneStatus, ...],
        progress: tuple[MilestoneProgress, ...],
    ) -> tuple[MilestoneHealth, ...]:
        progress_by_name = {item.name: item for item in progress}
        health: list[MilestoneHealth] = []

        for milestone in milestones:
            summary = progress_by_name[milestone.name]
            if summary.total == 0:
                status = "untracked"
                reason = "no linked actions"
            elif summary.completed == summary.total:
                status = "complete"
                reason = "all linked actions completed"
            elif milestone.is_overdue:
                status = "at-risk"
                reason = "deadline passed with incomplete work"
            elif milestone.days_from_brief <= 3 and (summary.blocked or summary.pending):
                status = "at-risk"
                reason = "deadline is near with blocked or dependency-waiting work"
            elif milestone.days_from_brief <= 7:
                status = "watch"
                reason = "deadline is within seven days with incomplete work"
            elif summary.blocked:
                status = "watch"
                reason = "linked work is blocked"
            else:
                status = "on-track"
                reason = "remaining work is not currently deadline-constrained"
            health.append(MilestoneHealth(milestone.name, status, reason))

        return tuple(health)

    @staticmethod
    def _milestone_attention(
        milestones: tuple[MilestoneStatus, ...],
        progress: tuple[MilestoneProgress, ...],
        health: tuple[MilestoneHealth, ...],
    ) -> tuple[MilestoneAttention, ...]:
        progress_by_name = {item.name: item for item in progress}
        health_by_name = {item.name: item for item in health}
        attention: list[MilestoneAttention] = []

        for milestone in milestones:
            milestone_health = health_by_name[milestone.name]
            if milestone_health.status not in {"at-risk", "watch"}:
                continue
            summary = progress_by_name[milestone.name]
            attention.append(
                MilestoneAttention(
                    name=milestone.name,
                    status=milestone_health.status,
                    reason=milestone_health.reason,
                    days_from_brief=milestone.days_from_brief,
                    completed=summary.completed,
                    total=summary.total,
                    pending=summary.pending,
                    blocked=summary.blocked,
                )
            )

        status_rank = {"at-risk": 0, "watch": 1}
        return tuple(
            sorted(
                attention,
                key=lambda item: (
                    status_rank[item.status],
                    item.days_from_brief,
                    item.name,
                ),
            )
        )

    @staticmethod
    def _milestone_interventions(
        attention: tuple[MilestoneAttention, ...],
    ) -> tuple[MilestoneIntervention, ...]:
        interventions: list[MilestoneIntervention] = []
        for item in attention:
            if item.blocked and item.pending:
                suggestion = "Resolve blocked work, then review dependency-waiting actions."
            elif item.blocked:
                suggestion = "Resolve blocked milestone work before the deadline becomes critical."
            elif item.pending:
                suggestion = (
                    "Review dependency-waiting actions and unblock the earliest prerequisite."
                )
            elif item.days_from_brief < 0:
                suggestion = (
                    "Review incomplete overdue work and decide what must be completed or deferred."
                )
            elif item.days_from_brief <= 3:
                suggestion = "Prioritise remaining milestone work before the imminent deadline."
            else:
                suggestion = (
                    "Review remaining milestone work while there is still scheduling flexibility."
                )
            interventions.append(MilestoneIntervention(item.name, item.status, suggestion))
        return tuple(interventions)
