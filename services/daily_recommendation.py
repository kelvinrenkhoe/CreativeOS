"""Recommend the next phase-aware campaign direction."""

from dataclasses import dataclass

from services.campaign_planner import CampaignPlan


@dataclass(frozen=True, slots=True)
class DailyRecommendation:
    """Reviewable direction for one campaign week."""

    work_id: str
    work_name: str
    week: int
    total_weeks: int
    phase_number: int
    phase_id: str
    phase_title: str
    narrative_focus: str
    campaign_objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]

    def render(self) -> str:
        """Render deterministic Markdown for the CLI and human review."""
        return "\n".join(
            (
                f"# Next Recommendation: {self.work_name}",
                "",
                f"**Campaign week:** {self.week} of {self.total_weeks}",
                f"**Active phase:** {self.phase_number} — {self.phase_title}",
                f"**Narrative focus:** {self.narrative_focus}",
                f"**Campaign objective:** {self.campaign_objective}",
                f"**Audience:** {self.audience}",
                f"**Tone:** {self.tone}",
                f"**Platforms:** {', '.join(self.platforms)}",
            )
        )


class DailyRecommendationService:
    """Select the active direction from a coordinated campaign plan."""

    @staticmethod
    def recommend(plan: CampaignPlan, *, week: int) -> DailyRecommendation:
        """Return a deterministic recommendation for a one-based campaign week."""
        direction = plan.direction_for_week(week)
        return DailyRecommendation(
            work_id=plan.work_id,
            work_name=plan.work_name,
            week=week,
            total_weeks=plan.total_weeks,
            phase_number=direction.phase_number,
            phase_id=direction.phase_id,
            phase_title=direction.title,
            narrative_focus=direction.narrative_objective,
            campaign_objective=direction.campaign_objective,
            audience=direction.audience,
            tone=direction.tone,
            platforms=direction.platforms,
        )
