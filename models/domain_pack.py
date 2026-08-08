"""Generic domain pack metadata for CreativeOS campaign templates."""

import re
from dataclasses import dataclass
from typing import Any

_IDENTIFIER = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class DomainPackError(ValueError):
    """Raised when domain pack metadata is invalid."""


@dataclass(frozen=True, slots=True)
class DomainPack:
    """Reusable domain configuration that points to campaign execution templates."""

    pack_id: str
    name: str
    description: str = ""
    template_ids: tuple[str, ...] = ()
    default_template_id: str | None = None

    def __post_init__(self) -> None:
        pack_id = _identifier(self.pack_id, "pack_id")
        name = self.name.strip()
        description = self.description.strip()
        template_ids = tuple(
            dict.fromkeys(_identifier(item, "template_id") for item in self.template_ids)
        )
        default_template_id = (
            None
            if self.default_template_id is None
            else _identifier(self.default_template_id, "default_template_id")
        )

        if not name:
            raise DomainPackError("name must be a non-empty string")
        if default_template_id is not None and default_template_id not in template_ids:
            raise DomainPackError("default_template_id must reference a declared template")

        object.__setattr__(self, "pack_id", pack_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "template_ids", template_ids)
        object.__setattr__(self, "default_template_id", default_template_id)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DomainPack":
        """Build a domain pack from parsed YAML metadata."""
        if not isinstance(data, dict):
            raise DomainPackError("domain pack must be a mapping")

        pack_id = data.get("id")
        name = data.get("name")
        description = data.get("description", "")
        template_ids = data.get("templates", [])
        default_template_id = data.get("default_template")

        if not isinstance(pack_id, str):
            raise DomainPackError("domain_pack.id is required")
        if not isinstance(name, str):
            raise DomainPackError("domain_pack.name is required")
        if not isinstance(description, str):
            raise DomainPackError("domain_pack.description must be a string")
        if not isinstance(template_ids, list) or not all(
            isinstance(item, str) for item in template_ids
        ):
            raise DomainPackError("domain_pack.templates must be a list of strings")
        if default_template_id is not None and not isinstance(default_template_id, str):
            raise DomainPackError("domain_pack.default_template must be a string")

        return cls(
            pack_id=pack_id,
            name=name,
            description=description,
            template_ids=tuple(template_ids),
            default_template_id=default_template_id,
        )


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise DomainPackError(f"{field_name} must be a string")
    normalized = value.strip().casefold().replace("_", "-").replace(" ", "-")
    if not _IDENTIFIER.fullmatch(normalized):
        raise DomainPackError(f"{field_name} must be a safe identifier")
    return normalized
