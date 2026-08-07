"""Organization-scoped project models for CreativeOS."""

import re
from dataclasses import dataclass
from typing import Any

_PROJECT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class ProjectContextError(ValueError):
    """Raised when organization project metadata is invalid."""


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Immutable project identity beneath a CreativeOS organization."""

    project_id: str
    name: str
    project_type: str = "custom"
    description: str = ""

    def __post_init__(self) -> None:
        project_id = self.project_id.strip().casefold()
        name = self.name.strip()
        project_type = self.project_type.strip().casefold().replace(" ", "-")
        description = self.description.strip()

        if not _PROJECT_ID.fullmatch(project_id):
            raise ProjectContextError(
                "project_id must contain only lowercase letters, numbers, and internal hyphens"
            )
        if not name:
            raise ProjectContextError("name must be a non-empty string")
        if not project_type or not _PROJECT_ID.fullmatch(project_type):
            raise ProjectContextError("project_type must be a path-safe identifier")

        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "project_type", project_type)
        object.__setattr__(self, "description", description)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectContext":
        """Build a project context from parsed YAML data."""
        if not isinstance(data, dict):
            raise ProjectContextError("project configuration must be a mapping")

        project_id = data.get("id")
        name = data.get("name")
        project_type = data.get("type", "custom")
        description = data.get("description", "")

        if not isinstance(project_id, str):
            raise ProjectContextError("project.id is required")
        if not isinstance(name, str):
            raise ProjectContextError("project.name is required")
        if not isinstance(project_type, str):
            raise ProjectContextError("project.type must be a string")
        if not isinstance(description, str):
            raise ProjectContextError("project.description must be a string")

        return cls(
            project_id=project_id,
            name=name,
            project_type=project_type,
            description=description,
        )
