"""Immutable models for deterministic platform-aware captions."""

from dataclasses import dataclass
from enum import StrEnum


class CaptionError(ValueError):
    """Reject invalid or inconsistent caption input."""


class CaptionPlatform(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    X = "x"
    WHATSAPP = "whatsapp"


class CaptionStructure(StrEnum):
    HOOK_STORY_CTA = "hook_story_cta"
    QUESTION_INSIGHT_CTA = "question_insight_cta"
    STATEMENT_CONTEXT_CTA = "statement_context_cta"
    MOMENT_MESSAGE_CTA = "moment_message_cta"
    SHORT_HOOK_CTA = "short_hook_cta"


@dataclass(frozen=True, slots=True)
class CaptionHistory:
    """Explicit content elements that must not be repeated."""

    hooks: tuple[str, ...] = ()
    calls_to_action: tuple[str, ...] = ()
    emotional_angles: tuple[str, ...] = ()
    hashtags: tuple[str, ...] = ()
    structures: tuple[CaptionStructure, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("hooks", "calls_to_action", "emotional_angles", "hashtags"):
            values = tuple(item.strip() for item in getattr(self, field_name))
            if any(not item for item in values):
                raise CaptionError(f"{field_name} must contain non-empty strings")
            object.__setattr__(self, field_name, values)
        if len(self.structures) != len(set(self.structures)):
            raise CaptionError("structures must be unique")


@dataclass(frozen=True, slots=True)
class CaptionRequest:
    """Explicit platform and novelty requirements for one caption package."""

    platforms: tuple[CaptionPlatform, ...]
    history: CaptionHistory = CaptionHistory()

    def __post_init__(self) -> None:
        if not self.platforms:
            raise CaptionError("platforms must not be empty")
        if any(not isinstance(item, CaptionPlatform) for item in self.platforms):
            raise CaptionError("platforms must contain CaptionPlatform values")
        if len(self.platforms) != len(set(self.platforms)):
            raise CaptionError("platforms must be unique")


@dataclass(frozen=True, slots=True)
class CaptionVariant:
    """One deterministic caption tailored to a platform."""

    caption_id: str
    platform: CaptionPlatform
    structure: CaptionStructure
    hook: str
    emotional_angle: str
    body: str
    call_to_action: str
    hashtags: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "caption_id",
            "hook",
            "emotional_angle",
            "body",
            "call_to_action",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise CaptionError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        hashtags = tuple(item.strip() for item in self.hashtags)
        if any(not item for item in hashtags):
            raise CaptionError("hashtags must contain non-empty strings")
        object.__setattr__(self, "hashtags", hashtags)

    def render(self) -> str:
        parts = [self.hook, self.body, self.call_to_action]
        if self.hashtags:
            parts.append(" ".join(self.hashtags))
        return "\n\n".join(parts)


@dataclass(frozen=True, slots=True)
class CaptionSet:
    """Ordered platform-specific captions for one campaign week."""

    caption_set_id: str
    campaign_id: str
    campaign_name: str
    campaign_week: int
    variants: tuple[CaptionVariant, ...]

    def __post_init__(self) -> None:
        if self.campaign_week < 1:
            raise CaptionError("campaign_week must be at least 1")
        if not self.variants:
            raise CaptionError("variants must not be empty")
        caption_ids = tuple(item.caption_id for item in self.variants)
        if len(caption_ids) != len(set(caption_ids)):
            raise CaptionError("caption IDs must be unique")

    def render(self) -> str:
        lines = [
            f"# Captions: {self.campaign_name}",
            "",
            f"Campaign week: {self.campaign_week}",
        ]
        for variant in self.variants:
            lines.extend(("", f"## {variant.platform.value}", variant.render()))
        return "\n".join(lines)
