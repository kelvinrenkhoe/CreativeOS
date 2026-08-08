"""Generic campaign content inventory models."""

import re
from dataclasses import dataclass
from typing import Any

from models.creative_brief import ContentCreativeBrief, CreativeBriefError

_CONTENT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_METADATA_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class ContentItemError(ValueError):
    """Raised when campaign content inventory metadata is invalid."""


@dataclass(frozen=True, slots=True)
class ContentItem:
    """One planned campaign content item and its production brief."""

    content_id: str
    title: str
    brief: ContentCreativeBrief
    content_role: str | None = None
    content_format: str | None = None
    channel: str | None = None
    action_id: str | None = None

    def __post_init__(self) -> None:
        content_id = _normalize_id(self.content_id, "content_id")
        title = self.title.strip()
        if not title:
            raise ContentItemError("title must be a non-empty string")
        if not isinstance(self.brief, ContentCreativeBrief):
            raise ContentItemError("brief must be a ContentCreativeBrief")

        object.__setattr__(self, "content_id", content_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(
            self,
            "content_role",
            _optional_metadata(self.content_role, "content_role"),
        )
        object.__setattr__(
            self,
            "content_format",
            _optional_metadata(self.content_format, "content_format"),
        )
        object.__setattr__(self, "channel", _optional_metadata(self.channel, "channel"))
        object.__setattr__(self, "action_id", _optional_id(self.action_id, "action_id"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContentItem":
        """Build a content item from parsed YAML data."""
        if not isinstance(data, dict):
            raise ContentItemError("content item configuration must be a mapping")

        content_id = data.get("id")
        title = data.get("title")
        brief_data = data.get("brief")
        if not isinstance(content_id, str):
            raise ContentItemError("content.id is required")
        if not isinstance(title, str):
            raise ContentItemError("content.title is required")
        for field_name in ("content_role", "content_format", "channel", "action_id"):
            value = data.get(field_name)
            if value is not None and not isinstance(value, str):
                raise ContentItemError(f"content.{field_name} must be a string")

        try:
            brief = ContentCreativeBrief.from_dict(brief_data)
        except CreativeBriefError as exc:
            raise ContentItemError(f"invalid content brief: {exc}") from exc

        return cls(
            content_id=content_id,
            title=title,
            brief=brief,
            content_role=data.get("content_role"),
            content_format=data.get("content_format"),
            channel=data.get("channel"),
            action_id=data.get("action_id"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return serializable content inventory metadata."""
        data: dict[str, object] = {
            "id": self.content_id,
            "title": self.title,
            "brief": self.brief.to_dict(),
        }
        for field_name in ("content_role", "content_format", "channel", "action_id"):
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value
        return data


def _normalize_id(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ContentItemError(f"{field_name} must be a string")
    normalized = value.strip().casefold().replace("_", "-").replace(" ", "-")
    if not _CONTENT_ID.fullmatch(normalized):
        raise ContentItemError(f"{field_name} must be a path-safe identifier")
    return normalized


def _optional_id(value: str | None, field_name: str) -> str | None:
    return None if value is None else _normalize_id(value, field_name)


def _optional_metadata(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContentItemError(f"{field_name} must be a string")
    normalized = value.strip().casefold().replace("_", "-").replace(" ", "-")
    if not _METADATA_ID.fullmatch(normalized):
        raise ContentItemError(f"{field_name} must be a safe identifier")
    return normalized
