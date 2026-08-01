"""Immutable models for deterministic Creative Studio planning."""

from dataclasses import dataclass
from enum import StrEnum


class CreativeStudioError(ValueError):
    """Reject invalid or inconsistent Creative Studio input."""


class DeliverableType(StrEnum):
    """Supported planned creative deliverables."""

    CAPTION = "caption"
    IMAGE_PROMPT = "image_prompt"
    VIDEO_PROMPT = "video_prompt"
    STORYBOARD = "storyboard"
    THUMBNAIL = "thumbnail"
    VOICEOVER = "voiceover"
    RADIO_SCRIPT = "radio_script"
    PRESS_ARTICLE = "press_article"
    PLAYLIST_PITCH = "playlist_pitch"


@dataclass(frozen=True, slots=True)
class StudioRequest:
    """Explicit weekly Creative Studio planning request."""

    campaign_id: str
    campaign_week: int
    deliverable_types: tuple[DeliverableType, ...]

    def __post_init__(self) -> None:
        campaign_id = self.campaign_id.strip()
        if not campaign_id:
            raise CreativeStudioError("campaign_id must be a non-empty string")
        if self.campaign_week < 1:
            raise CreativeStudioError("campaign_week must be at least 1")
        if not self.deliverable_types:
            raise CreativeStudioError("deliverable_types must not be empty")
        if any(not isinstance(item, DeliverableType) for item in self.deliverable_types):
            raise CreativeStudioError("deliverable_types must contain DeliverableType values")
        if len(self.deliverable_types) != len(set(self.deliverable_types)):
            raise CreativeStudioError("deliverable_types must be unique")
        object.__setattr__(self, "campaign_id", campaign_id)


@dataclass(frozen=True, slots=True)
class CreativeDeliverable:
    """One planned creative deliverable."""

    deliverable_id: str
    deliverable_type: DeliverableType
    campaign_week: int
    objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]
    source_item_id: str | None


@dataclass(frozen=True, slots=True)
class StudioOutput:
    """Deterministic weekly package of creative deliverables."""

    campaign_id: str
    campaign_name: str
    campaign_week: int
    deliverables: tuple[CreativeDeliverable, ...]

    def render(self) -> str:
        """Render the planned package as deterministic Markdown."""
        lines = (
            f"# Creative Studio: {self.campaign_name}",
            "",
            f"Campaign ID: {self.campaign_id}",
            f"Campaign week: {self.campaign_week}",
            "",
            "## Deliverables",
            *(
                f"- {item.deliverable_id}: {item.deliverable_type.value}"
                for item in self.deliverables
            ),
        )
        return "\n".join(lines)
