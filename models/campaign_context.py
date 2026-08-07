"""Organization project-scoped campaign models for CreativeOS."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

_CAMPAIGN_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class CampaignContextError(ValueError):
    """Raised when project campaign metadata is invalid."""


@dataclass(frozen=True, slots=True)
class CampaignContext:
    """Immutable campaign identity beneath a CreativeOS organization project."""

    campaign_id: str
    name: str
    campaign_type: str = "custom"
    status: str = "draft"
    objective: str = ""
    start_date: date | None = None
    end_date: date | None = None
    channels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        campaign_id = self.campaign_id.strip().casefold()
        name = self.name.strip()
        campaign_type = self.campaign_type.strip().casefold().replace(" ", "-")
        status = self.status.strip().casefold().replace(" ", "-")
        objective = self.objective.strip()
        channels = tuple(channel.strip().casefold() for channel in self.channels)

        if not _CAMPAIGN_ID.fullmatch(campaign_id):
            raise CampaignContextError(
                "campaign_id must contain only lowercase letters, numbers, and internal hyphens"
            )
        if not name:
            raise CampaignContextError("name must be a non-empty string")
        if not campaign_type or not _CAMPAIGN_ID.fullmatch(campaign_type):
            raise CampaignContextError("campaign_type must be a path-safe identifier")
        if not status or not _CAMPAIGN_ID.fullmatch(status):
            raise CampaignContextError("status must be a path-safe identifier")
        if any(not channel or not _CAMPAIGN_ID.fullmatch(channel) for channel in channels):
            raise CampaignContextError("channels must contain only path-safe identifiers")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise CampaignContextError("end_date cannot be before start_date")

        object.__setattr__(self, "campaign_id", campaign_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "campaign_type", campaign_type)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "channels", channels)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CampaignContext":
        """Build a campaign context from parsed YAML data."""
        if not isinstance(data, dict):
            raise CampaignContextError("campaign configuration must be a mapping")

        campaign_id = data.get("id")
        name = data.get("name")
        campaign_type = data.get("type", "custom")
        status = data.get("status", "draft")
        objective = data.get("objective", "")
        channels = data.get("channels", [])

        if not isinstance(campaign_id, str):
            raise CampaignContextError("campaign.id is required")
        if not isinstance(name, str):
            raise CampaignContextError("campaign.name is required")
        if not isinstance(campaign_type, str):
            raise CampaignContextError("campaign.type must be a string")
        if not isinstance(status, str):
            raise CampaignContextError("campaign.status must be a string")
        if not isinstance(objective, str):
            raise CampaignContextError("campaign.objective must be a string")
        if not isinstance(channels, list) or not all(isinstance(item, str) for item in channels):
            raise CampaignContextError("campaign.channels must be a list of strings")

        return cls(
            campaign_id=campaign_id,
            name=name,
            campaign_type=campaign_type,
            status=status,
            objective=objective,
            start_date=_parse_optional_date(data.get("start_date"), "start_date"),
            end_date=_parse_optional_date(data.get("end_date"), "end_date"),
            channels=tuple(channels),
        )


def _parse_optional_date(value: Any, field_name: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CampaignContextError(f"campaign.{field_name} must be an ISO date") from exc
    raise CampaignContextError(f"campaign.{field_name} must be an ISO date")
