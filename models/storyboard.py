"""Immutable models for deterministic cinematic storyboards."""

from dataclasses import dataclass
from enum import StrEnum


class StoryboardError(ValueError):
    """Reject invalid or inconsistent storyboard input."""


class CameraShot(StrEnum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    DETAIL = "detail"


class CameraMovement(StrEnum):
    STATIC = "static"
    PAN = "pan"
    TRACK = "track"
    PUSH_IN = "push_in"


class LightingStyle(StrEnum):
    NATURAL = "natural"
    LOW_KEY = "low_key"
    GOLDEN_HOUR = "golden_hour"
    PRACTICAL = "practical"


class SceneMood(StrEnum):
    REFLECTIVE = "reflective"
    DETERMINED = "determined"
    HOPEFUL = "hopeful"
    TRIUMPHANT = "triumphant"


class SceneTransition(StrEnum):
    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE = "fade"
    MATCH_CUT = "match_cut"


@dataclass(frozen=True, slots=True)
class StoryboardScene:
    scene_number: int
    duration_seconds: int
    location: str
    characters: tuple[str, ...]
    action: str
    emotion: str
    shot: CameraShot
    movement: CameraMovement
    lighting: LightingStyle
    mood: SceneMood
    music_cue: str
    transition: SceneTransition

    def __post_init__(self) -> None:
        if self.scene_number < 1:
            raise StoryboardError("scene_number must be at least 1")
        if self.duration_seconds < 1:
            raise StoryboardError("duration_seconds must be at least 1")
        for field_name in ("location", "action", "emotion", "music_cue"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise StoryboardError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        normalized = tuple(item.strip() for item in self.characters)
        if not normalized or any(not item for item in normalized):
            raise StoryboardError("characters must contain non-empty strings")
        object.__setattr__(self, "characters", normalized)


@dataclass(frozen=True, slots=True)
class Storyboard:
    storyboard_id: str
    campaign_id: str
    campaign_name: str
    campaign_week: int
    title: str
    objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]
    call_to_action: str
    scenes: tuple[StoryboardScene, ...]

    def __post_init__(self) -> None:
        if not self.scenes:
            raise StoryboardError("scenes must not be empty")
        expected = tuple(range(1, len(self.scenes) + 1))
        actual = tuple(scene.scene_number for scene in self.scenes)
        if actual != expected:
            raise StoryboardError("scenes must be numbered sequentially")

    @property
    def total_duration_seconds(self) -> int:
        return sum(scene.duration_seconds for scene in self.scenes)

    def render(self) -> str:
        lines = [
            f"# Storyboard: {self.title}",
            "",
            f"Campaign: {self.campaign_name}",
            f"Week: {self.campaign_week}",
            f"Duration: {self.total_duration_seconds}s",
            f"CTA: {self.call_to_action}",
        ]
        for scene in self.scenes:
            lines.extend(
                (
                    "",
                    f"## Scene {scene.scene_number} — {scene.duration_seconds}s",
                    f"Location: {scene.location}",
                    f"Characters: {', '.join(scene.characters)}",
                    f"Action: {scene.action}",
                    f"Emotion: {scene.emotion}",
                    f"Shot: {scene.shot.value}",
                    f"Movement: {scene.movement.value}",
                    f"Lighting: {scene.lighting.value}",
                    f"Mood: {scene.mood.value}",
                    f"Music cue: {scene.music_cue}",
                    f"Transition: {scene.transition.value}",
                )
            )
        return "\n".join(lines)
