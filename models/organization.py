"""Organization models for CreativeOS workspace isolation."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

_ORGANIZATION_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class OrganizationError(ValueError):
    """Raised when organization metadata is invalid."""


class OrganizationType(StrEnum):
    """Supported organization categories without changing core platform behavior."""

    CREATOR_BUSINESS = "creator_business"
    NONPROFIT = "nonprofit"
    BUSINESS = "business"
    AGENCY = "agency"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class Organization:
    """Immutable identity and configuration for one CreativeOS organization."""

    organization_id: str
    name: str
    organization_type: OrganizationType = OrganizationType.CUSTOM
    description: str = ""

    def __post_init__(self) -> None:
        organization_id = self.organization_id.strip().casefold()
        name = self.name.strip()
        description = self.description.strip()

        if not _ORGANIZATION_ID.fullmatch(organization_id):
            raise OrganizationError(
                "organization_id must contain only lowercase letters, numbers, and internal hyphens"
            )
        if not name:
            raise OrganizationError("name must be a non-empty string")
        if not isinstance(self.organization_type, OrganizationType):
            raise OrganizationError("organization_type must be an OrganizationType")

        object.__setattr__(self, "organization_id", organization_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Organization":
        """Build an organization from parsed YAML data."""
        if not isinstance(data, dict):
            raise OrganizationError("organization configuration must be a mapping")

        organization_id = data.get("id")
        name = data.get("name")
        organization_type = data.get("type", OrganizationType.CUSTOM.value)
        description = data.get("description", "")

        if not isinstance(organization_id, str):
            raise OrganizationError("organization.id is required")
        if not isinstance(name, str):
            raise OrganizationError("organization.name is required")
        if not isinstance(organization_type, str):
            raise OrganizationError("organization.type must be a string")
        if not isinstance(description, str):
            raise OrganizationError("organization.description must be a string")

        try:
            parsed_type = OrganizationType(organization_type)
        except ValueError as exc:
            raise OrganizationError(f"unsupported organization type: {organization_type}") from exc

        return cls(
            organization_id=organization_id,
            name=name,
            organization_type=parsed_type,
            description=description,
        )
