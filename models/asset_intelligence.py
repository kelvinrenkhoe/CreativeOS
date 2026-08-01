"""Immutable models for deterministic creative asset intelligence."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256


class AssetIntelligenceError(ValueError):
    """Reject invalid creative asset intelligence input."""


class AssetType(StrEnum):
    """Supported creative asset categories."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CAPTION = "caption"
    PROMPT = "prompt"
    STORYBOARD = "storyboard"
    VOICE_OVER = "voice_over"
    DOCUMENT = "document"


class AssetStatus(StrEnum):
    """Lifecycle states recorded without implying publication outcomes."""

    PLANNED = "planned"
    GENERATED = "generated"
    APPROVED = "approved"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class AssetUsage:
    """One explicit use of a creative asset."""

    platform: str
    purpose: str
    campaign_week: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "platform", _required(self.platform, "platform"))
        object.__setattr__(self, "purpose", _required(self.purpose, "purpose"))
        if self.campaign_week is not None and self.campaign_week < 1:
            raise AssetIntelligenceError("campaign_week must be at least 1")


@dataclass(frozen=True, slots=True)
class CreativeAsset:
    """Structured metadata for one creative asset."""

    asset_id: str
    campaign_id: str
    project_id: str
    asset_type: AssetType
    concept: str
    hook: str
    call_to_action: str
    platform: str
    file_path: str | None = None
    source_prompt: str | None = None
    campaign_week: int | None = None
    tags: tuple[str, ...] = ()
    descriptors: tuple[str, ...] = ()
    usages: tuple[AssetUsage, ...] = ()
    status: AssetStatus = AssetStatus.PLANNED

    def __post_init__(self) -> None:
        for field_name in (
            "asset_id",
            "campaign_id",
            "project_id",
            "concept",
            "hook",
            "call_to_action",
            "platform",
        ):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), field_name))
        if not isinstance(self.asset_type, AssetType):
            raise AssetIntelligenceError("asset_type must be an AssetType")
        if not isinstance(self.status, AssetStatus):
            raise AssetIntelligenceError("status must be an AssetStatus")
        if self.campaign_week is not None and self.campaign_week < 1:
            raise AssetIntelligenceError("campaign_week must be at least 1")
        object.__setattr__(self, "file_path", _optional(self.file_path))
        object.__setattr__(self, "source_prompt", _optional(self.source_prompt))
        object.__setattr__(self, "tags", _normalized_values(self.tags, "tag"))
        object.__setattr__(self, "descriptors", _normalized_values(self.descriptors, "descriptor"))

    @property
    def fingerprint_tokens(self) -> tuple[str, ...]:
        """Return stable normalized semantic tokens for similarity checks."""
        text = " ".join(
            (
                self.concept,
                self.hook,
                self.call_to_action,
                self.platform,
                *self.tags,
                *self.descriptors,
            )
        ).casefold()
        return tuple(sorted(set(re.findall(r"[a-z0-9]+", text))))

    @property
    def fingerprint(self) -> str:
        """Return a stable digest for the normalized creative direction."""
        return sha256("|".join(self.fingerprint_tokens).encode("utf-8")).hexdigest()


def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssetIntelligenceError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _normalized_values(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_required(value, field_name).casefold() for value in values)
    if len(normalized) != len(set(normalized)):
        raise AssetIntelligenceError(f"{field_name}s must be unique")
    return tuple(sorted(normalized))
