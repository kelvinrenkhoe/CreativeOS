"""Immutable models for deterministic scene-level image prompts."""

from dataclasses import dataclass
from enum import StrEnum


class ImagePromptError(ValueError):
    """Reject invalid image prompt input."""


class AspectRatio(StrEnum):
    SQUARE = "1:1"
    PORTRAIT = "4:5"
    VERTICAL = "9:16"
    LANDSCAPE = "16:9"


class VisualStyle(StrEnum):
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    EDITORIAL = "editorial"
    MINIMAL = "minimal"


@dataclass(frozen=True, slots=True)
class SceneImagePrompt:
    """One production-ready image prompt mapped to a storyboard scene."""

    prompt_id: str
    scene_number: int
    subject: str
    action: str
    location: str
    composition: str
    lighting: str
    mood: str
    wardrobe: str
    props: tuple[str, ...]
    continuity_notes: str
    aspect_ratio: AspectRatio
    visual_style: VisualStyle
    negative_constraints: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.scene_number < 1:
            raise ImagePromptError("scene_number must be at least 1")
        for field_name in (
            "prompt_id",
            "subject",
            "action",
            "location",
            "composition",
            "lighting",
            "mood",
            "wardrobe",
            "continuity_notes",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ImagePromptError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        object.__setattr__(self, "props", _normalize(self.props, "props"))
        object.__setattr__(
            self,
            "negative_constraints",
            _normalize(self.negative_constraints, "negative_constraints"),
        )

    def render(self) -> str:
        """Render this scene prompt deterministically."""
        return ", ".join(
            (
                self.subject,
                self.action,
                self.location,
                self.composition,
                self.lighting,
                self.mood,
                self.wardrobe,
                f"props: {', '.join(self.props)}",
                f"continuity: {self.continuity_notes}",
                f"style: {self.visual_style.value}",
                f"aspect ratio: {self.aspect_ratio.value}",
                f"avoid: {', '.join(self.negative_constraints)}",
            )
        )


@dataclass(frozen=True, slots=True)
class ImagePromptSet:
    """Ordered image prompts for one storyboard."""

    prompt_set_id: str
    campaign_id: str
    campaign_name: str
    campaign_week: int
    storyboard_id: str
    prompts: tuple[SceneImagePrompt, ...]

    def __post_init__(self) -> None:
        if not self.prompts:
            raise ImagePromptError("prompts must not be empty")
        expected = tuple(range(1, len(self.prompts) + 1))
        actual = tuple(prompt.scene_number for prompt in self.prompts)
        if actual != expected:
            raise ImagePromptError("prompts must follow storyboard scene order")
        prompt_ids = tuple(prompt.prompt_id for prompt in self.prompts)
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ImagePromptError("prompt IDs must be unique")

    def render(self) -> str:
        """Render the prompt set as deterministic Markdown."""
        lines = [
            f"# Image Prompts: {self.campaign_name}",
            "",
            f"Campaign week: {self.campaign_week}",
            f"Storyboard: {self.storyboard_id}",
        ]
        for prompt in self.prompts:
            lines.extend(("", f"## Scene {prompt.scene_number}", prompt.render()))
        return "\n".join(lines)


def _normalize(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if not normalized or any(not value for value in normalized):
        raise ImagePromptError(f"{field_name} must contain non-empty strings")
    return normalized
