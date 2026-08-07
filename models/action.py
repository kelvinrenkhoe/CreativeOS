"""Executable marketing action models for CreativeOS campaigns."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

_ACTION_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_ALLOWED_STATUSES = frozenset({"pending", "in-progress", "blocked", "completed", "cancelled"})
_ALLOWED_PRIORITIES = frozenset({"low", "normal", "high", "critical"})


class ActionError(ValueError):
    """Raised when campaign action metadata is invalid."""


@dataclass(frozen=True, slots=True)
class Action:
    """Immutable unit of executable marketing work within a campaign."""

    action_id: str
    title: str
    description: str = ""
    status: str = "pending"
    priority: str = "normal"
    due_date: date | None = None
    channel: str | None = None
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        action_id = _normalize_identifier(self.action_id, "action_id")
        title = self.title.strip()
        description = self.description.strip()
        status = self.status.strip().casefold().replace(" ", "-")
        priority = self.priority.strip().casefold()
        channel = None if self.channel is None else _normalize_identifier(self.channel, "channel")
        depends_on = tuple(
            dict.fromkeys(_normalize_identifier(item, "depends_on") for item in self.depends_on)
        )

        if not title:
            raise ActionError("title must be a non-empty string")
        if status not in _ALLOWED_STATUSES:
            allowed = ", ".join(sorted(_ALLOWED_STATUSES))
            raise ActionError(f"status must be one of: {allowed}")
        if priority not in _ALLOWED_PRIORITIES:
            allowed = ", ".join(sorted(_ALLOWED_PRIORITIES))
            raise ActionError(f"priority must be one of: {allowed}")
        if action_id in depends_on:
            raise ActionError("action cannot depend on itself")

        object.__setattr__(self, "action_id", action_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "priority", priority)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "depends_on", depends_on)

    @property
    def completed(self) -> bool:
        """Return whether the action is completed."""
        return self.status == "completed"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        """Build an action from parsed YAML data."""
        if not isinstance(data, dict):
            raise ActionError("action configuration must be a mapping")

        action_id = data.get("id")
        title = data.get("title")
        description = data.get("description", "")
        status = data.get("status", "pending")
        priority = data.get("priority", "normal")
        channel = data.get("channel")
        depends_on = data.get("depends_on", [])

        if not isinstance(action_id, str):
            raise ActionError("action.id is required")
        if not isinstance(title, str):
            raise ActionError("action.title is required")
        if not isinstance(description, str):
            raise ActionError("action.description must be a string")
        if not isinstance(status, str):
            raise ActionError("action.status must be a string")
        if not isinstance(priority, str):
            raise ActionError("action.priority must be a string")
        if channel is not None and not isinstance(channel, str):
            raise ActionError("action.channel must be a string")
        valid_dependencies = isinstance(depends_on, list) and all(
            isinstance(item, str) for item in depends_on
        )
        if not valid_dependencies:
            raise ActionError("action.depends_on must be a list of strings")

        return cls(
            action_id=action_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_date=_parse_optional_date(data.get("due_date")),
            channel=channel,
            depends_on=tuple(depends_on),
        )


def _normalize_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ActionError(f"{field_name} must be a string")
    normalized = value.strip().casefold().replace(" ", "-")
    if not _ACTION_ID.fullmatch(normalized):
        raise ActionError(f"{field_name} must be a path-safe identifier")
    return normalized


def _parse_optional_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ActionError("action.due_date must be an ISO date") from exc
    raise ActionError("action.due_date must be an ISO date")
