"""Campaign-scoped production asset and deliverable metadata."""

import re
from dataclasses import dataclass
from typing import Any

_ASSET_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_METADATA_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_ALLOWED_STATUSES = ("planned", "draft", "review", "approved", "published")


class CampaignAssetError(ValueError):
    """Raised when campaign asset metadata is invalid."""


@dataclass(frozen=True, slots=True)
class CampaignAsset:
    """One campaign deliverable tracked through its production lifecycle."""

    asset_id: str
    title: str
    asset_type: str
    status: str = "planned"
    content_id: str | None = None
    channel: str | None = None
    location: str | None = None
    action_id: str | None = None

    def __post_init__(self) -> None:
        asset_id = _normalize_id(self.asset_id, "asset_id")
        title = self.title.strip()
        if not title:
            raise CampaignAssetError("title must be a non-empty string")
        asset_type = _normalize_metadata(self.asset_type, "asset_type")
        status = self.status.strip().casefold()
        if status not in _ALLOWED_STATUSES:
            allowed = ", ".join(_ALLOWED_STATUSES)
            raise CampaignAssetError(f"status must be one of: {allowed}")

        object.__setattr__(self, "asset_id", asset_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "asset_type", asset_type)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "content_id", _optional_id(self.content_id, "content_id"))
        object.__setattr__(self, "channel", _optional_metadata(self.channel, "channel"))
        object.__setattr__(self, "action_id", _optional_id(self.action_id, "action_id"))
        object.__setattr__(self, "location", _optional_text(self.location, "location"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CampaignAsset":
        """Build an asset record from parsed YAML data."""
        if not isinstance(data, dict):
            raise CampaignAssetError("asset configuration must be a mapping")
        for required in ("id", "title", "type"):
            if not isinstance(data.get(required), str):
                raise CampaignAssetError(f"asset.{required} is required")
        for field_name in ("status", "content_id", "channel", "location", "action_id"):
            value = data.get(field_name)
            if value is not None and not isinstance(value, str):
                raise CampaignAssetError(f"asset.{field_name} must be a string")
        return cls(
            asset_id=data["id"],
            title=data["title"],
            asset_type=data["type"],
            status=data.get("status", "planned"),
            content_id=data.get("content_id"),
            channel=data.get("channel"),
            location=data.get("location"),
            action_id=data.get("action_id"),
        )

    def to_dict(self) -> dict[str, str]:
        """Return compact serializable asset metadata."""
        data = {
            "id": self.asset_id,
            "title": self.title,
            "type": self.asset_type,
            "status": self.status,
        }
        for field_name in ("content_id", "channel", "location", "action_id"):
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value
        return data


def _normalize_id(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise CampaignAssetError(f"{field_name} must be a string")
    normalized = value.strip().casefold().replace("_", "-").replace(" ", "-")
    if not _ASSET_ID.fullmatch(normalized):
        raise CampaignAssetError(f"{field_name} must be a path-safe identifier")
    return normalized


def _normalize_metadata(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise CampaignAssetError(f"{field_name} must be a string")
    normalized = value.strip().casefold().replace("_", "-").replace(" ", "-")
    if not _METADATA_ID.fullmatch(normalized):
        raise CampaignAssetError(f"{field_name} must be a safe identifier")
    return normalized


def _optional_id(value: str | None, field_name: str) -> str | None:
    return None if value is None else _normalize_id(value, field_name)


def _optional_metadata(value: str | None, field_name: str) -> str | None:
    return None if value is None else _normalize_metadata(value, field_name)


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CampaignAssetError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise CampaignAssetError(f"{field_name} must not be empty")
    return normalized
