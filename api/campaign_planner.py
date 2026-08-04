"""Deterministic forward-looking campaign planning API."""

from dataclasses import dataclass
from datetime import date, timedelta

from api.campaign_manager import CampaignManagerAPI
from api.campaign_tasks import CampaignTask, CampaignTasksAPI
from api.campaign_timeline import CampaignTimelineAPI
from core.project import Project


@dataclass(frozen=True, slots=True)
class DailyPlan:
    """Planned campaign activity for one calendar date."""

    date: date
    tasks: tuple[CampaignTask, ...] = ()
    milestone: str | None = None
    priority: str = "none"
    estimated_minutes: int = 0


@dataclass(frozen=True, slots=True)
class CampaignPlanResult:
    """Structured multi-day campaign plan."""

    campaign: str
    start: date
    end: date
    daily_plans: tuple[DailyPlan, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether the plan was generated without errors."""
        return not self.errors


class CampaignPlannerAPI:
    """Compose existing campaign APIs into a deterministic execution plan."""

    def __init__(
        self,
        project: Project,
        *,
        tasks_api: CampaignTasksAPI | None = None,
        timeline_api: CampaignTimelineAPI | None = None,
        manager_api: CampaignManagerAPI | None = None,
    ) -> None:
        self.tasks_api = tasks_api or CampaignTasksAPI(project)
        self.timeline_api = timeline_api or CampaignTimelineAPI(project)
        self.manager_api = manager_api or CampaignManagerAPI(project)

    def plan(
        self,
        campaign_name: str,
        *,
        days: int = 7,
        today: date | None = None,
    ) -> CampaignPlanResult:
        """Return a deterministic campaign plan for an inclusive date window."""
        start = today or date.today()
        if days < 1:
            return CampaignPlanResult(
                campaign=campaign_name,
                start=start,
                end=start,
                errors=("days must be at least 1",),
            )

        end = start + timedelta(days=days - 1)
        tasks = self.tasks_api.today(campaign_name, today=start)
        timeline = self.timeline_api.timeline(campaign_name)
        manager = self.manager_api.today(campaign_name, today=start)
        warnings = self._unique(tasks.warnings + timeline.warnings + manager.warnings)
        errors = self._unique(tasks.errors + timeline.errors + manager.errors)

        if errors:
            return CampaignPlanResult(
                campaign=campaign_name,
                start=start,
                end=end,
                warnings=warnings,
                errors=errors,
            )

        tasks_by_date: dict[date, list[CampaignTask]] = {start: list(tasks.overdue)}
        for task in tasks.due_today + tasks.upcoming:
            task_date = task.scheduled_for.date()
            if start <= task_date <= end:
                tasks_by_date.setdefault(task_date, []).append(task)

        milestones = {
            event.date: event.title
            for event in timeline.timeline_events
            if start <= event.date <= end
        }

        daily_plans = tuple(
            self._daily_plan(
                day,
                tuple(tasks_by_date.get(day, ())),
                milestones.get(day),
                manager.task if day == start else None,
            )
            for day in (start + timedelta(days=offset) for offset in range(days))
        )

        return CampaignPlanResult(
            campaign=campaign_name,
            start=start,
            end=end,
            daily_plans=daily_plans,
            warnings=warnings,
        )

    def _daily_plan(
        self,
        day: date,
        tasks: tuple[CampaignTask, ...],
        milestone: str | None,
        manager_task: CampaignTask | None,
    ) -> DailyPlan:
        ordered = tuple(
            sorted(
                tasks,
                key=lambda task: (
                    -task.priority,
                    task.scheduled_for,
                    task.request_id,
                ),
            )
        )
        if manager_task is not None and manager_task in ordered:
            priority = "high"
        elif ordered:
            priority = "normal"
        elif milestone:
            priority = "milestone"
        else:
            priority = "none"

        return DailyPlan(
            date=day,
            tasks=ordered,
            milestone=milestone,
            priority=priority,
            estimated_minutes=sum(self._estimated_minutes(task) for task in ordered),
        )

    @staticmethod
    def _estimated_minutes(task: CampaignTask) -> int:
        media_type = task.media_type.casefold()
        asset_id = task.asset_id.casefold()
        if "caption" in media_type or "caption" in asset_id:
            return 10
        if "image" in media_type or "image" in asset_id:
            return 10
        if "audio" in media_type or "audio" in asset_id:
            return 20
        if "video" in media_type or "video" in asset_id:
            return 30
        if "review" in media_type or "review" in asset_id:
            return 15
        return 20

    @staticmethod
    def _unique(messages: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(messages))
