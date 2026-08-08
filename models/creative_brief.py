"""Immutable models for campaign and content creative context."""

from dataclasses import dataclass
from typing import Any


class CreativeBriefError(ValueError):
    """Reject invalid or inconsistent creative brief input."""


@dataclass(frozen=True, slots=True)
class ContentCreativeBrief:
    """Generic production intent for one campaign content item."""

    objective: str
    audience: str
    key_message: str
    call_to_action: str = ""
    production_notes: str = ""
    approval_expectations: str = ""

    def __post_init__(self) -> None:
        for field_name in ("objective", "audience", "key_message"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise CreativeBriefError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())

        for field_name in (
            "call_to_action",
            "production_notes",
            "approval_expectations",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise CreativeBriefError(f"{field_name} must be a string")
            object.__setattr__(self, field_name, value.strip())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContentCreativeBrief":
        """Build a content brief from parsed configuration data."""
        if not isinstance(data, dict):
            raise CreativeBriefError("creative_brief must be a mapping")
        return cls(
            objective=_string_value(data, "objective", required=True),
            audience=_string_value(data, "audience", required=True),
            key_message=_string_value(data, "key_message", required=True),
            call_to_action=_string_value(data, "call_to_action"),
            production_notes=_string_value(data, "production_notes"),
            approval_expectations=_string_value(data, "approval_expectations"),
        )

    def to_dict(self) -> dict[str, str]:
        """Return compact serializable brief metadata."""
        data = {
            "objective": self.objective,
            "audience": self.audience,
            "key_message": self.key_message,
        }
        for field_name in (
            "call_to_action",
            "production_notes",
            "approval_expectations",
        ):
            value = getattr(self, field_name)
            if value:
                data[field_name] = value
        return data


@dataclass(frozen=True, slots=True)
class CreativeBriefRequest:
    """Explicit campaign identity and direction supplied by the caller."""

    campaign_id: str
    campaign_name: str
    artist: str
    objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]
    knowledge: str = ""
    story_context: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "campaign_id",
            "campaign_name",
            "artist",
            "objective",
            "audience",
            "tone",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise CreativeBriefError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())

        normalized_platforms = tuple(platform.strip() for platform in self.platforms)
        if not normalized_platforms or any(not platform for platform in normalized_platforms):
            raise CreativeBriefError("platforms must contain non-empty strings")
        if len(normalized_platforms) != len(set(normalized_platforms)):
            raise CreativeBriefError("platforms must be unique")

        object.__setattr__(self, "platforms", normalized_platforms)
        object.__setattr__(self, "knowledge", self.knowledge.strip())
        object.__setattr__(self, "story_context", self.story_context.strip())


@dataclass(frozen=True, slots=True)
class CreativeBriefBlockedItem:
    """One blocked campaign item and its unmet prerequisites."""

    item_id: str
    unmet_prerequisite_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreativeBriefRecovery:
    """Optional recovery context included in a creative brief."""

    changed: bool
    recovered_item_ids: tuple[str, ...]
    fixed_milestone_ids: tuple[str, ...]
    moved_item_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreativeBrief:
    """Unified read-only context for downstream creative generation."""

    campaign_id: str
    campaign_name: str
    artist: str
    objective: str
    audience: str
    tone: str
    platforms: tuple[str, ...]
    knowledge: str
    story_context: str
    memory: str
    completed_item_ids: tuple[str, ...]
    ready_item_ids: tuple[str, ...]
    blocked_items: tuple[CreativeBriefBlockedItem, ...]
    next_item_id: str | None
    next_reason: str | None
    recovery: CreativeBriefRecovery | None

    def render(self) -> str:
        """Render the brief as deterministic Markdown."""
        blocked = (
            "\n".join(
                f"- {item.item_id}: {', '.join(item.unmet_prerequisite_ids)}"
                for item in self.blocked_items
            )
            or "- None"
        )
        recovery = "Not supplied."
        if self.recovery is not None:
            recovery = "\n".join(
                (
                    f"Changed: {self.recovery.changed}",
                    f"Recovered order: {', '.join(self.recovery.recovered_item_ids)}",
                    f"Fixed milestones: {', '.join(self.recovery.fixed_milestone_ids) or 'None'}",
                    f"Moved items: {', '.join(self.recovery.moved_item_ids) or 'None'}",
                )
            )

        return "\n".join(
            (
                f"# Creative Brief: {self.campaign_name}",
                "",
                f"Artist: {self.artist}",
                f"Campaign ID: {self.campaign_id}",
                f"Objective: {self.objective}",
                f"Audience: {self.audience}",
                f"Tone: {self.tone}",
                f"Platforms: {', '.join(self.platforms)}",
                "",
                "## Knowledge",
                self.knowledge,
                "",
                "## Story Context",
                self.story_context,
                "",
                "## Campaign Memory",
                self.memory,
                "",
                "## Execution",
                f"Completed: {', '.join(self.completed_item_ids) or 'None'}",
                f"Ready: {', '.join(self.ready_item_ids) or 'None'}",
                f"Next: {self.next_item_id or 'None'}",
                f"Reason: {self.next_reason or 'None'}",
                "",
                "### Blocked",
                blocked,
                "",
                "## Recovery",
                recovery,
            )
        )


def _string_value(data: dict[str, Any], name: str, *, required: bool = False) -> str:
    value = data.get(name)
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise CreativeBriefError(f"creative_brief.{name} must be a string")
    return value
