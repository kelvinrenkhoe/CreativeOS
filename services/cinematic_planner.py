"""Build provider-agnostic cinematic treatments from campaign direction."""

from dataclasses import dataclass

from services.campaign_planner import CampaignPlan, CampaignPhaseDirection
from story.context import StoryContext


@dataclass(frozen=True, slots=True)
class ShotDirection:
    """One visual instruction within a cinematic scene."""

    number: int
    framing: str
    movement: str
    description: str


@dataclass(frozen=True, slots=True)
class CinematicScene:
    """A phase-aligned scene with grounded visual direction."""

    number: int
    phase_id: str
    title: str
    narrative_purpose: str
    setting: str
    subjects: tuple[str, ...]
    motifs: tuple[str, ...]
    mood: str
    shots: tuple[ShotDirection, ...]


@dataclass(frozen=True, slots=True)
class CinematicTreatment:
    """A reviewable cinematic plan for one creative work."""

    work_id: str
    work_name: str
    concept: str
    audience: str
    platforms: tuple[str, ...]
    visual_motifs: tuple[str, ...]
    scenes: tuple[CinematicScene, ...]

    def scene_for_phase(self, phase_id: str) -> CinematicScene:
        """Return the scene assigned to a campaign phase."""
        for scene in self.scenes:
            if scene.phase_id == phase_id:
                return scene
        raise KeyError(f"cinematic scene not found for phase: {phase_id}")

    def render(self) -> str:
        """Render deterministic Markdown for review and downstream consumers."""
        lines = [
            f"# Cinematic Treatment: {self.work_name}",
            "",
            f"**Concept:** {self.concept}",
            f"**Audience:** {self.audience}",
            f"**Platforms:** {', '.join(self.platforms)}",
            f"**Visual motifs:** {', '.join(self.visual_motifs) or 'None defined'}",
        ]
        for scene in self.scenes:
            lines.extend(
                [
                    "",
                    f"## Scene {scene.number}: {scene.title}",
                    "",
                    f"**Narrative purpose:** {scene.narrative_purpose}",
                    f"**Setting:** {scene.setting}",
                    f"**Subjects:** {', '.join(scene.subjects) or 'Unspecified'}",
                    f"**Motifs:** {', '.join(scene.motifs) or 'None defined'}",
                    f"**Mood:** {scene.mood}",
                    "",
                    "### Shots",
                ]
            )
            lines.extend(
                f"{shot.number}. **{shot.framing} / {shot.movement}:** {shot.description}"
                for shot in scene.shots
            )
        return "\n".join(lines)


class CinematicPlannerService:
    """Transform story and campaign direction into a cinematic treatment."""

    def build(self, context: StoryContext, plan: CampaignPlan) -> CinematicTreatment:
        """Build deterministic scenes without generating prompts or media."""
        self._validate(context, plan)
        motifs = self._motifs(context)
        settings = tuple(location.name for location in context.locations)
        subjects = tuple(character.name for character in context.characters)

        return CinematicTreatment(
            work_id=plan.work_id,
            work_name=plan.work_name,
            concept=(
                f"{plan.intent.tone} visual storytelling that supports "
                f"{plan.intent.objective.lower()}."
            ),
            audience=plan.intent.audience,
            platforms=plan.intent.platforms,
            visual_motifs=motifs,
            scenes=tuple(
                self._scene(
                    phase,
                    setting=settings[index % len(settings)] if settings else "Story world",
                    subjects=subjects,
                    motifs=motifs,
                )
                for index, phase in enumerate(plan.phases)
            ),
        )

    @staticmethod
    def _validate(context: StoryContext, plan: CampaignPlan) -> None:
        if plan.work_id != context.work.id:
            raise ValueError(
                f"campaign plan work '{plan.work_id}' does not match context work "
                f"'{context.work.id}'"
            )
        if not plan.phases:
            raise ValueError("campaign plan must contain at least one phase")

    @staticmethod
    def _motifs(context: StoryContext) -> tuple[str, ...]:
        symbols = tuple(symbol.name for symbol in context.symbols)
        if symbols:
            return symbols
        return tuple(theme.name for theme in context.themes)

    @staticmethod
    def _scene(
        phase: CampaignPhaseDirection,
        *,
        setting: str,
        subjects: tuple[str, ...],
        motifs: tuple[str, ...],
    ) -> CinematicScene:
        focus = phase.narrative_objective.rstrip(".")
        shots = (
            ShotDirection(
                number=1,
                framing="Wide establishing shot",
                movement="Slow push",
                description=f"Introduce {setting} and establish {focus.lower()}.",
            ),
            ShotDirection(
                number=2,
                framing="Medium character shot",
                movement="Controlled tracking",
                description="Follow the central subject through the phase's emotional action.",
            ),
            ShotDirection(
                number=3,
                framing="Close detail",
                movement="Locked frame",
                description=(
                    f"End on the visual motif {motifs[0]}."
                    if motifs
                    else "End on a meaningful story detail."
                ),
            ),
        )
        return CinematicScene(
            number=phase.phase_number,
            phase_id=phase.phase_id,
            title=phase.title,
            narrative_purpose=phase.narrative_objective,
            setting=setting,
            subjects=subjects,
            motifs=motifs,
            mood=phase.tone,
            shots=shots,
        )
