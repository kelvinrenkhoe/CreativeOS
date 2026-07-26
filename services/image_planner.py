"""Build provider-agnostic image and poster plans from campaign direction."""

from dataclasses import dataclass

from services.campaign_planner import CampaignPhaseDirection, CampaignPlan
from story.context import StoryContext


@dataclass(frozen=True, slots=True)
class ImageFormat:
    """A reusable presentation format for an image concept."""

    name: str
    aspect_ratio: str
    composition: str
    typography: str


@dataclass(frozen=True, slots=True)
class ImageConcept:
    """A phase-aligned visual concept with explicit continuity constraints."""

    number: int
    phase_id: str
    title: str
    narrative_purpose: str
    setting: str
    subjects: tuple[str, ...]
    identity_reference: str
    wardrobe: str
    motifs: tuple[str, ...]
    mood: str
    exclusions: tuple[str, ...]
    formats: tuple[ImageFormat, ...]

    def format(self, name: str) -> ImageFormat:
        """Return a format variant by its normalized name."""
        normalized = name.strip().casefold()
        for image_format in self.formats:
            if image_format.name == normalized:
                return image_format
        raise KeyError(f"image format not found: {name}")


@dataclass(frozen=True, slots=True)
class ImagePlan:
    """A reviewable, provider-neutral image plan for one creative work."""

    work_id: str
    work_name: str
    audience: str
    platforms: tuple[str, ...]
    visual_direction: str
    concepts: tuple[ImageConcept, ...]

    def concept_for_phase(self, phase_id: str) -> ImageConcept:
        """Return the image concept assigned to a campaign phase."""
        for concept in self.concepts:
            if concept.phase_id == phase_id:
                return concept
        raise KeyError(f"image concept not found for phase: {phase_id}")

    def render(self) -> str:
        """Render deterministic Markdown for review and downstream adapters."""
        lines = [
            f"# Image Plan: {self.work_name}",
            "",
            f"**Audience:** {self.audience}",
            f"**Platforms:** {', '.join(self.platforms)}",
            f"**Visual direction:** {self.visual_direction}",
        ]
        for concept in self.concepts:
            lines.extend(
                [
                    "",
                    f"## Concept {concept.number}: {concept.title}",
                    "",
                    f"**Narrative purpose:** {concept.narrative_purpose}",
                    f"**Setting:** {concept.setting}",
                    f"**Subjects:** {', '.join(concept.subjects) or 'Unspecified'}",
                    f"**Identity:** {concept.identity_reference}",
                    f"**Wardrobe:** {concept.wardrobe}",
                    f"**Motifs:** {', '.join(concept.motifs) or 'None defined'}",
                    f"**Mood:** {concept.mood}",
                    f"**Exclusions:** {', '.join(concept.exclusions)}",
                    "",
                    "### Format variants",
                ]
            )
            lines.extend(
                f"- **{item.name} ({item.aspect_ratio}):** "
                f"{item.composition} Typography: {item.typography}"
                for item in concept.formats
            )
        return "\n".join(lines)


class ImagePlannerService:
    """Transform story and campaign direction into reusable image concepts."""

    _FORMATS = (
        ImageFormat(
            name="cover-art",
            aspect_ratio="1:1",
            composition="Iconic focal subject with restrained negative space.",
            typography="Title and artist text permitted when requested.",
        ),
        ImageFormat(
            name="poster",
            aspect_ratio="4:5",
            composition="Cinematic subject hierarchy with space for campaign copy.",
            typography="Use a clear title hierarchy; keep text away from faces.",
        ),
        ImageFormat(
            name="social-graphic",
            aspect_ratio="4:5",
            composition="Immediate mobile-first focal point with safe crop margins.",
            typography="Short campaign copy permitted; prioritize legibility.",
        ),
        ImageFormat(
            name="thumbnail",
            aspect_ratio="16:9",
            composition="High-contrast subject and motif readable at small size.",
            typography="Use no more than a short headline.",
        ),
        ImageFormat(
            name="cinematic-still",
            aspect_ratio="16:9",
            composition="Narrative frame with natural depth and no promotional layout.",
            typography="No text.",
        ),
    )
    _EXCLUSIONS = (
        "identity drift",
        "duplicate subjects",
        "distorted hands",
        "unreadable text",
        "watermarks",
        "unrequested logos",
    )

    def build(self, context: StoryContext, plan: CampaignPlan) -> ImagePlan:
        """Build deterministic concepts without calling an image provider."""
        self._validate(context, plan)
        subjects = tuple(character.name for character in context.characters)
        settings = tuple(location.name for location in context.locations)
        motifs = self._motifs(context)

        return ImagePlan(
            work_id=plan.work_id,
            work_name=plan.work_name,
            audience=plan.intent.audience,
            platforms=plan.intent.platforms,
            visual_direction=(
                f"{plan.intent.tone} imagery supporting {plan.intent.objective.lower()}."
            ),
            concepts=tuple(
                self._concept(
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

    @classmethod
    def _concept(
        cls,
        phase: CampaignPhaseDirection,
        *,
        setting: str,
        subjects: tuple[str, ...],
        motifs: tuple[str, ...],
    ) -> ImageConcept:
        subject_text = ", ".join(subjects) or "the central subject"
        return ImageConcept(
            number=phase.phase_number,
            phase_id=phase.phase_id,
            title=phase.title,
            narrative_purpose=phase.narrative_objective,
            setting=setting,
            subjects=subjects,
            identity_reference=(
                f"Preserve the approved appearance and defining features of {subject_text}."
            ),
            wardrobe=(
                "Use one phase-specific wardrobe and preserve its colours, materials, "
                "and accessories across every format."
            ),
            motifs=motifs,
            mood=phase.tone,
            exclusions=cls._EXCLUSIONS,
            formats=cls._FORMATS,
        )
