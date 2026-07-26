"""Build objective-driven, provider-agnostic campaign plans."""

from dataclasses import dataclass

from story.context import StoryContext
from story.timeline import NarrativeTimeline, TimelinePhase


@dataclass(frozen=True, slots=True)
class CampaignIntent:
    """Human-supplied direction that constrains a campaign plan."""

    objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CampaignPhaseDirection:
    """Campaign direction for one narrative timeline phase."""

    phase_number: int
    phase_id: str
    title: str
    start_week: int
    end_week: int
    narrative_objective: str
    campaign_objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]

    @property
    def week_label(self) -> str:
        """Return a human-readable label for this phase's campaign weeks."""
        if self.start_week == self.end_week:
            return f"Week {self.start_week}"
        return f"Weeks {self.start_week}-{self.end_week}"


@dataclass(frozen=True, slots=True)
class CampaignPlan:
    """A coordinated campaign brief aligned to a narrative timeline."""

    work_id: str
    work_name: str
    total_weeks: int
    intent: CampaignIntent
    phases: tuple[CampaignPhaseDirection, ...]

    def direction_for_week(self, week: int) -> CampaignPhaseDirection:
        """Return campaign direction active during a one-based week."""
        if week < 1 or week > self.total_weeks:
            raise ValueError(f"week must be between 1 and {self.total_weeks}")
        return next(
            phase for phase in self.phases if phase.start_week <= week <= phase.end_week
        )

    def render(self) -> str:
        """Render deterministic Markdown for review and downstream consumers."""
        lines = [
            f"# Campaign Plan: {self.work_name}",
            "",
            f"**Objective:** {self.intent.objective}",
            f"**Audience:** {self.intent.audience}",
            f"**Tone:** {self.intent.tone}",
            f"**Platforms:** {', '.join(self.intent.platforms)}",
            f"**Campaign length:** {self.total_weeks} weeks",
        ]
        for phase in self.phases:
            lines.extend(
                [
                    "",
                    f"## Phase {phase.phase_number}: {phase.title}",
                    "",
                    f"**Timing:** {phase.week_label}",
                    f"**Narrative objective:** {phase.narrative_objective}",
                    f"**Campaign objective:** {phase.campaign_objective}",
                ]
            )
        return "\n".join(lines)


class CampaignPlannerService:
    """Combine story, timeline, and human intent into campaign direction."""

    def build(
        self,
        context: StoryContext,
        timeline: NarrativeTimeline,
        *,
        objective: str,
        audience: str,
        tone: str,
        platforms: tuple[str, ...],
    ) -> CampaignPlan:
        """Build a deterministic plan without generating campaign assets."""
        self._validate_timeline(context, timeline)
        intent = CampaignIntent(
            objective=self._required(objective, "objective"),
            audience=self._required(audience, "audience"),
            tone=self._required(tone, "tone"),
            platforms=self._platforms(platforms),
        )

        return CampaignPlan(
            work_id=context.work.id,
            work_name=context.work.name,
            total_weeks=timeline.total_weeks,
            intent=intent,
            phases=tuple(self._phase_direction(phase, intent) for phase in timeline.phases),
        )

    @staticmethod
    def _validate_timeline(context: StoryContext, timeline: NarrativeTimeline) -> None:
        if timeline.work_id != context.work.id:
            raise ValueError(
                f"timeline work '{timeline.work_id}' does not match context work "
                f"'{context.work.id}'"
            )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized

    @classmethod
    def _platforms(cls, platforms: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            dict.fromkeys(cls._required(platform, "platform").casefold() for platform in platforms)
        )
        if not normalized:
            raise ValueError("platforms must not be empty")
        return normalized

    @staticmethod
    def _phase_direction(
        phase: TimelinePhase,
        intent: CampaignIntent,
    ) -> CampaignPhaseDirection:
        return CampaignPhaseDirection(
            phase_number=phase.number,
            phase_id=phase.id,
            title=phase.title,
            start_week=phase.start_week,
            end_week=phase.end_week,
            narrative_objective=phase.objective,
            campaign_objective=intent.objective,
            audience=intent.audience,
            tone=intent.tone,
            platforms=intent.platforms,
        )
