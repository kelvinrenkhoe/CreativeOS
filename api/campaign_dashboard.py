"""Aggregate campaign APIs into one deterministic dashboard result."""

from dataclasses import dataclass
from datetime import date

from api.campaign_analytics import CampaignAnalyticsAPI
from api.campaign_tasks import CampaignTasksAPI
from api.campaign_timeline import CampaignTimelineAPI
from core.project import Project
from orchestrator import CampaignRuntimePreset, CampaignRuntimePresetRegistry, RuntimeStage
from services.campaign_doctor import CampaignDoctorService
from services.campaign_recommendations import CampaignRecommendationsService
from services.campaign_scoring import CampaignScoringService


@dataclass(frozen=True, slots=True)
class CampaignDashboardResult:
    """One structured campaign overview for user interfaces and agents."""

    campaign: str
    today: date
    readiness_score: int = 0
    readiness_label: str = "needs-attention"
    quality_score: int = 0
    current_phase: str = "Planning"
    completion_percent: int = 0
    overdue_task_count: int = 0
    due_today_count: int = 0
    next_milestone: str | None = None
    recommendation_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether every underlying dashboard source succeeded."""
        return not self.errors


class CampaignDashboardAPI:
    """Orchestrate existing campaign APIs without duplicating domain logic."""

    def __init__(
        self,
        project: Project,
        *,
        analytics_api: CampaignAnalyticsAPI | None = None,
        tasks_api: CampaignTasksAPI | None = None,
        timeline_api: CampaignTimelineAPI | None = None,
        doctor_service: CampaignDoctorService | None = None,
        scoring_service: CampaignScoringService | None = None,
        recommendations_service: CampaignRecommendationsService | None = None,
    ) -> None:
        self.project = project
        self.analytics_api = analytics_api or CampaignAnalyticsAPI(project)
        self.tasks_api = tasks_api or CampaignTasksAPI(project)
        self.timeline_api = timeline_api or CampaignTimelineAPI(project)
        self.doctor_service = doctor_service or CampaignDoctorService(
            project,
            self._doctor_registry(),
        )
        self.scoring_service = scoring_service or CampaignScoringService()
        self.recommendations_service = (
            recommendations_service or CampaignRecommendationsService()
        )

    def summary(
        self,
        campaign_name: str,
        *,
        today: date | None = None,
    ) -> CampaignDashboardResult:
        """Return one deterministic campaign dashboard summary."""
        reference_date = today or date.today()
        analytics = self.analytics_api.summary(campaign_name, today=reference_date)
        tasks = self.tasks_api.today(campaign_name, today=reference_date)
        timeline = self.timeline_api.status(campaign_name, today=reference_date)

        warnings = list(analytics.warnings + tasks.warnings + timeline.warnings)
        errors = list(analytics.errors + tasks.errors + timeline.errors)
        quality_score = 0
        recommendation_count = 0

        try:
            report = self.doctor_service.diagnose(
                campaign_name,
                context={"campaign": campaign_name},
            )
            quality_score = self.scoring_service.score(
                campaign_name,
                report,
            ).overall_score
            recommendation_count = len(
                self.recommendations_service.recommend(
                    campaign_name,
                    report,
                ).items
            )
        except ValueError as exc:
            errors.append(f"Campaign assessment failed: {exc}")

        unique_warnings = self._unique(warnings)
        unique_errors = self._unique(errors)

        return CampaignDashboardResult(
            campaign=campaign_name,
            today=reference_date,
            readiness_score=analytics.readiness_score,
            readiness_label=analytics.health,
            quality_score=quality_score,
            current_phase=timeline.current_phase,
            completion_percent=tasks.completion_percent,
            overdue_task_count=len(tasks.overdue),
            due_today_count=len(tasks.due_today),
            next_milestone=timeline.next_milestone,
            recommendation_count=recommendation_count,
            warning_count=len(unique_warnings),
            error_count=len(unique_errors),
            warnings=unique_warnings,
            errors=unique_errors,
        )

    @staticmethod
    def _unique(messages: list[str]) -> tuple[str, ...]:
        """Return messages once while preserving source order."""
        return tuple(dict.fromkeys(messages))

    @staticmethod
    def _doctor_registry() -> CampaignRuntimePresetRegistry:
        """Return the established music-release Doctor preset."""
        registry = CampaignRuntimePresetRegistry()
        registry.register(
            CampaignRuntimePreset(
                name="music-release",
                description="Validate a music-release campaign.",
                required_context_keys=("campaign",),
                stages=(
                    RuntimeStage(
                        "brief",
                        lambda campaign: campaign,
                        ("campaign",),
                        "brief",
                    ),
                ),
            )
        )
        return registry
