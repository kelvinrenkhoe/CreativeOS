"""Deterministic campaign manager orchestration API."""

from dataclasses import dataclass
from datetime import date

from api.campaign_dashboard import CampaignDashboardAPI
from api.campaign_tasks import CampaignTask, CampaignTasksAPI
from core.project import Project


@dataclass(frozen=True, slots=True)
class CampaignManagerResult:
    """One actionable campaign-management decision for a reference date."""

    campaign: str
    today: date
    priority_action: str | None = None
    reason: str | None = None
    task: CampaignTask | None = None
    current_phase: str = "Planning"
    next_milestone: str | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether the manager produced a result without errors."""
        return not self.errors


class CampaignManagerAPI:
    """Turn existing campaign APIs into one deterministic next action."""

    def __init__(
        self,
        project: Project,
        *,
        dashboard_api: CampaignDashboardAPI | None = None,
        tasks_api: CampaignTasksAPI | None = None,
    ) -> None:
        self.dashboard_api = dashboard_api or CampaignDashboardAPI(project)
        self.tasks_api = tasks_api or CampaignTasksAPI(project)

    def today(
        self,
        campaign_name: str,
        *,
        today: date | None = None,
    ) -> CampaignManagerResult:
        """Return the highest-priority safe action for one campaign today."""
        reference_date = today or date.today()
        dashboard = self.dashboard_api.summary(campaign_name, today=reference_date)
        tasks = self.tasks_api.today(campaign_name, today=reference_date)
        warnings = self._unique(dashboard.warnings + tasks.warnings)
        errors = self._unique(dashboard.errors + tasks.errors)

        if errors:
            return CampaignManagerResult(
                campaign=campaign_name,
                today=reference_date,
                current_phase=dashboard.current_phase,
                next_milestone=dashboard.next_milestone,
                warnings=warnings,
                errors=errors,
            )

        if tasks.overdue:
            task = tasks.overdue[0]
            return self._result(
                campaign_name,
                reference_date,
                dashboard.current_phase,
                dashboard.next_milestone,
                warnings,
                task,
                f"Complete overdue task: {task.asset_id}",
                f"Scheduled for {task.scheduled_for.date().isoformat()} and still incomplete.",
            )

        if tasks.due_today:
            task = tasks.due_today[0]
            return self._result(
                campaign_name,
                reference_date,
                dashboard.current_phase,
                dashboard.next_milestone,
                warnings,
                task,
                f"Complete today's task: {task.asset_id}",
                "This is the highest-priority task scheduled for today.",
            )

        if dashboard.next_milestone:
            return CampaignManagerResult(
                campaign=campaign_name,
                today=reference_date,
                priority_action=f"Prepare for milestone: {dashboard.next_milestone}",
                reason="No overdue or due-today execution tasks remain.",
                current_phase=dashboard.current_phase,
                next_milestone=dashboard.next_milestone,
                warnings=warnings,
            )

        return CampaignManagerResult(
            campaign=campaign_name,
            today=reference_date,
            priority_action="Review campaign readiness",
            reason="No scheduled task or upcoming milestone is currently available.",
            current_phase=dashboard.current_phase,
            warnings=warnings,
        )

    @staticmethod
    def _result(
        campaign: str,
        today: date,
        phase: str,
        milestone: str | None,
        warnings: tuple[str, ...],
        task: CampaignTask,
        action: str,
        reason: str,
    ) -> CampaignManagerResult:
        return CampaignManagerResult(
            campaign=campaign,
            today=today,
            priority_action=action,
            reason=reason,
            task=task,
            current_phase=phase,
            next_milestone=milestone,
            warnings=warnings,
        )

    @staticmethod
    def _unique(messages: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(messages))
