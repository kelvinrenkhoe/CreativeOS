"""Build provider-agnostic video prompts from cinematic treatments."""

from dataclasses import dataclass

from services.cinematic_planner import CinematicScene, CinematicTreatment, ShotDirection


@dataclass(frozen=True, slots=True)
class VideoShotPrompt:
    """A generator-neutral prompt for one video shot."""

    number: int
    duration_seconds: int
    setting: str
    subjects: tuple[str, ...]
    action: str
    framing: str
    movement: str
    mood: str
    motifs: tuple[str, ...]
    continuity: str

    def render(self) -> str:
        """Render a compact natural-language prompt."""
        subject_text = ", ".join(self.subjects) or "the central subject"
        motif_text = ", ".join(self.motifs) or "a meaningful story detail"
        return (
            f"{self.framing} in {self.setting}. {self.movement}. "
            f"Show {subject_text}: {self.action} "
            f"Use a {self.mood.lower()} mood and feature {motif_text}. "
            f"Continuity: {self.continuity}"
        )


@dataclass(frozen=True, slots=True)
class VideoScenePrompt:
    """All video prompts assigned to one cinematic scene."""

    number: int
    phase_id: str
    title: str
    narrative_purpose: str
    shots: tuple[VideoShotPrompt, ...]

    @property
    def duration_seconds(self) -> int:
        """Return the combined duration of the scene's shots."""
        return sum(shot.duration_seconds for shot in self.shots)


@dataclass(frozen=True, slots=True)
class VideoPrompt:
    """A reviewable, provider-neutral prompt package for one creative work."""

    work_id: str
    work_name: str
    concept: str
    audience: str
    platforms: tuple[str, ...]
    scenes: tuple[VideoScenePrompt, ...]

    @property
    def duration_seconds(self) -> int:
        """Return the combined duration of every scene."""
        return sum(scene.duration_seconds for scene in self.scenes)

    def scene_for_phase(self, phase_id: str) -> VideoScenePrompt:
        """Return the prompt scene assigned to a campaign phase."""
        for scene in self.scenes:
            if scene.phase_id == phase_id:
                return scene
        raise KeyError(f"video prompt scene not found for phase: {phase_id}")

    def render(self) -> str:
        """Render deterministic Markdown for review and provider adapters."""
        lines = [
            f"# Video Prompt: {self.work_name}",
            "",
            f"**Concept:** {self.concept}",
            f"**Audience:** {self.audience}",
            f"**Platforms:** {', '.join(self.platforms)}",
            f"**Duration:** {self.duration_seconds} seconds",
        ]
        for scene in self.scenes:
            lines.extend(
                [
                    "",
                    f"## Scene {scene.number}: {scene.title}",
                    "",
                    f"**Narrative purpose:** {scene.narrative_purpose}",
                    f"**Duration:** {scene.duration_seconds} seconds",
                    "",
                    "### Shot prompts",
                ]
            )
            lines.extend(
                f"{shot.number}. **{shot.duration_seconds}s:** {shot.render()}" for shot in scene.shots
            )
        return "\n".join(lines)


class VideoPromptService:
    """Translate cinematic treatments into provider-neutral video prompts."""

    def build(
        self,
        treatment: CinematicTreatment,
        *,
        seconds_per_shot: int = 5,
    ) -> VideoPrompt:
        """Build deterministic prompts without calling a video provider."""
        self._validate(treatment, seconds_per_shot)
        return VideoPrompt(
            work_id=treatment.work_id,
            work_name=treatment.work_name,
            concept=treatment.concept,
            audience=treatment.audience,
            platforms=treatment.platforms,
            scenes=tuple(
                self._scene(scene, seconds_per_shot=seconds_per_shot)
                for scene in treatment.scenes
            ),
        )

    @staticmethod
    def _validate(treatment: CinematicTreatment, seconds_per_shot: int) -> None:
        if not treatment.scenes:
            raise ValueError("cinematic treatment must contain at least one scene")
        if seconds_per_shot < 1:
            raise ValueError("seconds per shot must be at least 1")
        empty_scene = next((scene for scene in treatment.scenes if not scene.shots), None)
        if empty_scene is not None:
            raise ValueError(f"cinematic scene '{empty_scene.phase_id}' must contain a shot")

    @classmethod
    def _scene(
        cls,
        scene: CinematicScene,
        *,
        seconds_per_shot: int,
    ) -> VideoScenePrompt:
        continuity = cls._continuity(scene)
        return VideoScenePrompt(
            number=scene.number,
            phase_id=scene.phase_id,
            title=scene.title,
            narrative_purpose=scene.narrative_purpose,
            shots=tuple(
                cls._shot(
                    shot,
                    scene=scene,
                    continuity=continuity,
                    seconds_per_shot=seconds_per_shot,
                )
                for shot in scene.shots
            ),
        )

    @staticmethod
    def _shot(
        shot: ShotDirection,
        *,
        scene: CinematicScene,
        continuity: str,
        seconds_per_shot: int,
    ) -> VideoShotPrompt:
        return VideoShotPrompt(
            number=shot.number,
            duration_seconds=seconds_per_shot,
            setting=scene.setting,
            subjects=scene.subjects,
            action=shot.description,
            framing=shot.framing,
            movement=shot.movement,
            mood=scene.mood,
            motifs=scene.motifs,
            continuity=continuity,
        )

    @staticmethod
    def _continuity(scene: CinematicScene) -> str:
        subjects = ", ".join(scene.subjects) or "central subject"
        motifs = ", ".join(scene.motifs) or "story-world details"
        return f"Preserve the appearance of {subjects}, the setting, and {motifs} across shots."
