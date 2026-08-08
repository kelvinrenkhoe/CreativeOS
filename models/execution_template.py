"""Reusable execution template models for campaign action plans."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from models.action import Action, ActionError

_TEMPLATE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_VARIABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_METADATA_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_PLACEHOLDER = re.compile(r"{{\s*([a-z][a-z0-9_]*)(?:\s*([+-])\s*(\d+)d)?\s*}}")


class ExecutionTemplateError(ValueError):
    """Raised when an execution template is invalid."""


@dataclass(frozen=True, slots=True)
class TemplateVariable:
    name: str
    description: str = ""
    default: str | None = None
    required: bool = False

    def __post_init__(self) -> None:
        name = self.name.strip().casefold()
        if not _VARIABLE_ID.fullmatch(name):
            raise ExecutionTemplateError("template variable names must be safe identifiers")
        if self.required and self.default is not None:
            raise ExecutionTemplateError(f"template variable {name!r} cannot be required and have a default")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class ExecutionTemplate:
    template_id: str
    name: str
    description: str = ""
    actions: tuple[Action, ...] = ()
    variables: tuple[TemplateVariable, ...] = ()
    milestones: tuple[str, ...] = ()
    content_roles: tuple[str, ...] = ()
    content_formats: tuple[str, ...] = ()
    action_specs: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        template_id = self.template_id.strip().casefold()
        name = self.name.strip()
        milestones = tuple(item.strip().casefold() for item in self.milestones)
        content_roles = tuple(_normalize_metadata(item, "content roles") for item in self.content_roles)
        content_formats = tuple(_normalize_metadata(item, "content formats") for item in self.content_formats)
        if not _TEMPLATE_ID.fullmatch(template_id):
            raise ExecutionTemplateError("template_id must be a path-safe identifier")
        if not name:
            raise ExecutionTemplateError("name must be a non-empty string")
        if len({a.action_id for a in self.actions}) != len(self.actions):
            raise ExecutionTemplateError("template action ids must be unique")
        variable_names = [v.name for v in self.variables]
        if len(variable_names) != len(set(variable_names)):
            raise ExecutionTemplateError("template variable names must be unique")
        if len(milestones) != len(set(milestones)) or any(not _VARIABLE_ID.fullmatch(m) for m in milestones):
            raise ExecutionTemplateError("template milestone names must be unique safe identifiers")
        if len(content_roles) != len(set(content_roles)):
            raise ExecutionTemplateError("template content roles must be unique")
        if len(content_formats) != len(set(content_formats)):
            raise ExecutionTemplateError("template content formats must be unique")
        collisions = sorted(set(variable_names) & set(milestones))
        if collisions:
            raise ExecutionTemplateError(f"template variables and milestones cannot share names: {', '.join(collisions)}")
        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "milestones", milestones)
        object.__setattr__(self, "content_roles", content_roles)
        object.__setattr__(self, "content_formats", content_formats)
        self._validate_metadata(self.actions)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionTemplate":
        if not isinstance(data, dict):
            raise ExecutionTemplateError("execution template must be a mapping")
        raw_actions = data.get("actions", [])
        raw_variables = data.get("variables", {})
        raw_milestones = data.get("milestones", [])
        raw_roles = data.get("content_roles", [])
        raw_formats = data.get("content_formats", [])
        if not isinstance(data.get("id"), str):
            raise ExecutionTemplateError("template.id is required")
        if not isinstance(data.get("name"), str):
            raise ExecutionTemplateError("template.name is required")
        if not isinstance(data.get("description", ""), str):
            raise ExecutionTemplateError("template.description must be a string")
        if not isinstance(raw_actions, list):
            raise ExecutionTemplateError("template.actions must be a list")
        if not isinstance(raw_variables, dict):
            raise ExecutionTemplateError("template.variables must be a mapping")
        for value, field in ((raw_milestones, "milestones"), (raw_roles, "content_roles"), (raw_formats, "content_formats")):
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ExecutionTemplateError(f"template.{field} must be a list of strings")
        variables = tuple(_parse_variable(k, v) for k, v in raw_variables.items())
        if _contains_placeholder(raw_actions):
            action_specs = tuple(_copy_action_spec(item) for item in raw_actions)
            actions: tuple[Action, ...] = ()
        else:
            action_specs = ()
            try:
                actions = tuple(Action.from_dict(item) for item in raw_actions)
            except ActionError as exc:
                raise ExecutionTemplateError(f"invalid template action: {exc}") from exc
        template = cls(data["id"], data["name"], data.get("description", ""), actions, variables, tuple(raw_milestones), tuple(raw_roles), tuple(raw_formats), action_specs)
        template._validate_placeholders()
        return template

    def render_actions(self, values: dict[str, str] | None = None, milestones: dict[str, date] | None = None) -> tuple[Action, ...]:
        resolved = {**self._resolve_variables(values or {}), **self._resolve_milestones(milestones or {})}
        if not self.action_specs:
            return self.actions
        rendered = tuple(_render_value(spec, resolved) for spec in self.action_specs)
        try:
            actions = tuple(Action.from_dict(spec) for spec in rendered)
        except ActionError as exc:
            raise ExecutionTemplateError(f"invalid rendered template action: {exc}") from exc
        self._validate_metadata(actions)
        return actions

    def _resolve_variables(self, supplied: dict[str, str]) -> dict[str, str]:
        known = {v.name: v for v in self.variables}
        unknown = sorted(set(supplied) - set(known))
        if unknown:
            raise ExecutionTemplateError(f"unknown template variables: {', '.join(unknown)}")
        resolved, missing = {}, []
        for name, variable in known.items():
            if name in supplied:
                resolved[name] = supplied[name]
            elif variable.default is not None:
                resolved[name] = variable.default
            elif variable.required:
                missing.append(name)
        if missing:
            raise ExecutionTemplateError(f"missing required template variables: {', '.join(sorted(missing))}")
        return resolved

    def _resolve_milestones(self, available: dict[str, date]) -> dict[str, str]:
        missing = sorted(set(self.milestones) - set(available))
        if missing:
            raise ExecutionTemplateError(f"campaign is missing required milestones: {', '.join(missing)}")
        return {name: available[name].isoformat() for name in self.milestones}

    def _validate_placeholders(self) -> None:
        if not self.action_specs:
            return
        declared = {v.name for v in self.variables} | set(self.milestones)
        undeclared = sorted(_collect_placeholders(self.action_specs) - declared)
        if undeclared:
            raise ExecutionTemplateError(f"undeclared template values: {', '.join(undeclared)}")

    def _validate_metadata(self, actions: tuple[Action, ...]) -> None:
        used_roles = {a.content_role for a in actions if a.content_role is not None}
        used_formats = {a.content_format for a in actions if a.content_format is not None}
        undeclared_roles = sorted(used_roles - set(self.content_roles))
        undeclared_formats = sorted(used_formats - set(self.content_formats))
        if undeclared_roles:
            raise ExecutionTemplateError(f"undeclared template content roles: {', '.join(undeclared_roles)}")
        if undeclared_formats:
            raise ExecutionTemplateError(f"undeclared template content formats: {', '.join(undeclared_formats)}")


def _parse_variable(name: str, definition: Any) -> TemplateVariable:
    if not isinstance(name, str):
        raise ExecutionTemplateError("template variable names must be strings")
    if definition is None:
        return TemplateVariable(name=name, required=True)
    if isinstance(definition, str):
        return TemplateVariable(name=name, default=definition)
    if not isinstance(definition, dict):
        raise ExecutionTemplateError(f"template variable {name!r} must be a mapping")
    description, default = definition.get("description", ""), definition.get("default")
    required = definition.get("required", default is None)
    if not isinstance(description, str) or (default is not None and not isinstance(default, str)) or not isinstance(required, bool):
        raise ExecutionTemplateError(f"invalid template variable {name!r}")
    return TemplateVariable(name, description, default, required)


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str): return bool(_PLACEHOLDER.search(value))
    if isinstance(value, list): return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict): return any(_contains_placeholder(item) for item in value.values())
    return False


def _collect_placeholders(value: Any) -> set[str]:
    if isinstance(value, str): return {m.group(1) for m in _PLACEHOLDER.finditer(value)}
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in value: found.update(_collect_placeholders(item))
        return found
    if isinstance(value, dict):
        found = set()
        for item in value.values(): found.update(_collect_placeholders(item))
        return found
    return set()


def _render_value(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name, operator, days_text = match.group(1), match.group(2), match.group(3)
            if name not in variables: raise ExecutionTemplateError(f"template value {name!r} has no value")
            raw = variables[name]
            if operator is None: return raw
            try: anchor = date.fromisoformat(raw)
            except ValueError as exc: raise ExecutionTemplateError(f"template value {name!r} must be an ISO date for relative scheduling") from exc
            delta = timedelta(days=int(days_text) if operator == "+" else -int(days_text))
            return (anchor + delta).isoformat()
        return _PLACEHOLDER.sub(replace, value)
    if isinstance(value, list): return [_render_value(item, variables) for item in value]
    if isinstance(value, dict): return {key: _render_value(item, variables) for key, item in value.items()}
    return value


def _copy_action_spec(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict): raise ExecutionTemplateError("template action entries must be mappings")
    return dict(value)


def _normalize_metadata(value: str, label: str) -> str:
    normalized = value.strip().casefold().replace("_", "-").replace(" ", "-")
    if not _METADATA_ID.fullmatch(normalized): raise ExecutionTemplateError(f"template {label} must be safe identifiers")
    return normalized
