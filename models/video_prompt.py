"""Immutable models for deterministic scene-level video prompts."""

from dataclasses import dataclass
from enum import StrEnum


class VideoPromptError(ValueError):
    """Reject invalid video prompt input."""


class Pacing(StrEnum):
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"


class MotionIntensity(StrEnum):
    SUBTLE = "subtle"
    BALANCED = "balanced"
    DYNAMIC = "dynamic"


class ContinuityMode(StrEnum):
    STRICT = "strict"
    FLEXIBLE = "flexible"


@dataclass(frozen=True, slots=True)
class SceneVideoPrompt:
    """One provider-neutral video direction mapped to a storyboard scene."""

    prompt_id: str
    scene_number: int
    duration_seconds: int
    visual_reference_prompt_id: str
    camera_direction: str
    subject_motion: str
    environmental_motion: str
    transition_direction: str
    music_alignment: str
    continuity_notes: str
    pacing: Pacing
    motion_intensity: MotionIntensity
    provider_instructions: str

    def __post_init__(self) -> None:
        if self.scene_number < 1:
            raise VideoPromptError("scene_number must be at least 1")
        if self.duration_seconds < 1:
            raise VideoPromptError("duration_seconds must be at least 1")
        for field_name in (
            "prompt_id",
            "visual_reference_prompt_id",
            "camera_direction",
            "subject_motion",
            "environmental_motion",
            "transition_direction",
            "music_alignment",
            "continuity_notes",
            "provider_instructions",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise VideoPromptError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())

    def render(self) -> str:
        """Render this scene direction deterministically."""
        return "\n".join(
            (
                f"Duration: {self.duration_seconds}s",
                f"Visual reference: {self.visual_reference_prompt_id}",
                f"Camera: {self.camera_direction}",
                f"Subject motion: {self.subject_motion}",
                f"Environment: {self.environmental_motion}",
                f"Transition: {self.transition_direction}",
                f"Music: {self.music_alignment}",
                f"Continuity: {self.continuity_notes}",
                f"Pacing: {self.pacing.value}",
                f"Motion intensity: {self.motion_intensity.value}",
                f"Instructions: {self.provider_instructions}",
            )
        )


@dataclass(frozen=True, slots=True)
class VideoPromptSet:
    """Ordered video directions for one storyboard."""

    prompt_set_id: str
    campaign_id: str
    campaign_name: str
    campaign_week: int
    storyboard_id: str
    image_prompt_set_id: str
    continuity_mode: ContinuityMode
    prompts: tuple[SceneVideoPrompt, ...]

    def __post_init__(self) -> None:
        if not self.prompts:
            raise VideoPromptError("prompts must not be empty")
        expected = tuple(range(1, len(self.prompts) + 1))
        actual = tuple(prompt.scene_number for prompt in self.prompts)
        if actual != expected:
            raise VideoPromptError("prompts must follow storyboard scene order")
        prompt_ids = tuple(prompt.prompt_id for prompt in self.prompts)
        if len(prompt_ids) != len(set(prompt_ids)):
            raise VideoPromptError("prompt IDs must be unique")

    @property
    def total_duration_seconds(self) -> int:
        return sum(prompt.duration_seconds for prompt in self.prompts)

    def render(self) -> str:
        """Render the prompt set as deterministic Markdown."""
        lines = [
            f"# Video Prompts: {self.campaign_name}",
            "",
            f"Campaign week: {self.campaign_week}",
            f"Storyboard: {self.storyboard_id}",
            f"Image prompts: {self.image_prompt_set_id}",
            f"Duration: {self.total_duration_seconds}s",
            f"Continuity mode: {self.continuity_mode.value}",
        ]
        for prompt in self.prompts:
            lines.extend(("", f"## Scene {prompt.scene_number}", prompt.render()))
        return "\n".join(lines)
