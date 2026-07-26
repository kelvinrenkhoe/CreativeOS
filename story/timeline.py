"""Build deterministic, phase-aware narrative campaign timelines."""

from dataclasses import dataclass

from story.context import StoryContext
from story.models import StoryArc


@dataclass(frozen=True, slots=True)
class TimelinePhase:
    """One ordered campaign phase derived from a story beat."""

    number: int
    id: str
    title: str
    objective: str
    start_week: int
    end_week: int

    @property
    def duration_weeks(self) -> int:
        """Return the inclusive duration of this phase."""
        return self.end_week - self.start_week + 1


@dataclass(frozen=True, slots=True)
class NarrativeTimeline:
    """A work-specific narrative sequence distributed across campaign weeks."""

    work_id: str
    work_name: str
    arc_id: str
    arc_name: str
    total_weeks: int
    phases: tuple[TimelinePhase, ...]

    def phase_for_week(self, week: int) -> TimelinePhase:
        """Return the phase active during a one-based campaign week."""
        if week < 1 or week > self.total_weeks:
            raise ValueError(f"week must be between 1 and {self.total_weeks}")

        return next(
            phase for phase in self.phases if phase.start_week <= week <= phase.end_week
        )

    def render(self) -> str:
        """Render a deterministic Markdown campaign timeline."""
        lines = [
            f"# Narrative Timeline: {self.work_name}",
            "",
            f"**Story arc:** {self.arc_name}",
            f"**Campaign length:** {self.total_weeks} weeks",
        ]
        for phase in self.phases:
            week_label = (
                f"Week {phase.start_week}"
                if phase.start_week == phase.end_week
                else f"Weeks {phase.start_week}-{phase.end_week}"
            )
            lines.extend(
                [
                    "",
                    f"## Phase {phase.number}: {phase.title}",
                    "",
                    f"**Timing:** {week_label}",
                    f"**Objective:** {phase.objective}",
                ]
            )
        return "\n".join(lines)


class NarrativeTimelineService:
    """Turn Story Context arcs into ordered, phase-aware campaign timelines."""

    def build(
        self,
        context: StoryContext,
        *,
        weeks: int,
        arc_id: str | None = None,
    ) -> NarrativeTimeline:
        """Build a timeline from one selected story arc."""
        arc = self._select_arc(context, arc_id)
        if not arc.beats:
            raise ValueError(f"story arc has no beats: {arc.id}")
        if weeks < len(arc.beats):
            raise ValueError(
                f"campaign weeks ({weeks}) must cover all story beats ({len(arc.beats)})"
            )

        base_duration, remainder = divmod(weeks, len(arc.beats))
        phases: list[TimelinePhase] = []
        start_week = 1

        for index, beat in enumerate(arc.beats):
            duration = base_duration + (1 if index < remainder else 0)
            end_week = start_week + duration - 1
            phases.append(
                TimelinePhase(
                    number=index + 1,
                    id=beat.id,
                    title=beat.id.replace("-", " ").title(),
                    objective=beat.summary,
                    start_week=start_week,
                    end_week=end_week,
                )
            )
            start_week = end_week + 1

        return NarrativeTimeline(
            work_id=context.work.id,
            work_name=context.work.name,
            arc_id=arc.id,
            arc_name=arc.name,
            total_weeks=weeks,
            phases=tuple(phases),
        )

    @staticmethod
    def _select_arc(context: StoryContext, arc_id: str | None) -> StoryArc:
        if not context.arcs:
            raise ValueError(f"story context has no arcs: {context.work.id}")
        if arc_id is None:
            if len(context.arcs) > 1:
                raise ValueError("arc_id is required when story context contains multiple arcs")
            return context.arcs[0]

        for arc in context.arcs:
            if arc.id == arc_id:
                return arc
        raise KeyError(f"story arc not found in context: {arc_id}")
