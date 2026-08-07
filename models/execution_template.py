"""Reusable execution template models for campaign action plans."""

import re
from dataclasses import dataclass
from typing import Any

from models.action import Action, ActionError

_TEMPLATE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class ExecutionTemplateError(ValueError):
    """Raised when an execution template is invalid."""


@dataclass(frozen=True, slots=True)
class ExecutionTemplate:
    """Immutable reusable collection of campaign actions."""

    template_id: str
    name: str
    description: str = ""
    actions: tuple[Action, ...] = ()

    def __post_init__(self) -> None:
        template_id = self.template_id.strip().casefold()
        name = self.name.strip()
        description = self.description.strip()

        if not _TEMPLATE_ID.fullmatch(template_id):
            raise ExecutionTemplateError("template_id must be a path-safe identifier")
        if not name:
            raise ExecutionTemplateError("name must be a non-empty string")
        action_ids = [action.action_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ExecutionTemplateError("template action ids must be unique")

        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionTemplate":
        """Build an execution template from parsed YAML."""
        if not isinstance(data, dict):
            raise ExecutionTemplateError("execution template must be a mapping")

        template_id = data.get("id")
        name = data.get("name")
        description = data.get("description", "")
        raw_actions = data.get("actions", [])

        if not isinstance(template_id, str):
            raise ExecutionTemplateError("template.id is required")
        if not isinstance(name, str):
            raise ExecutionTemplateError("template.name is required")
        if not isinstance(description, str):
            raise ExecutionTemplateError("template.description must be a string")
        if not isinstance(raw_actions, list):
            raise ExecutionTemplateError("template.actions must be a list")

        try:
            actions = tuple(Action.from_dict(item) for item in raw_actions)
        except ActionError as exc:
            raise ExecutionTemplateError(f"invalid template action: {exc}") from exc

        return cls(
            template_id=template_id,
            name=name,
            description=description,
            actions=actions,
        )
