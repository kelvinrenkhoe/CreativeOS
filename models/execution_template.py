"""Reusable execution template models for campaign action plans."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from models.action import Action, ActionError

_TEMPLATE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_VARIABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_PLACEHOLDER = re.compile(r"{{\s*([a-z][a-z0-9_]*)(?:\s*([+-])\s*(\d+)d)?\s*}}")


class ExecutionTemplateError(ValueError):
    """Raised when an execution template is invalid."""


@dataclass(frozen=True, slots=True)
class TemplateVariable:
    """One reusable input accepted by an execution template."""

    name: str
    description: str = ""
    default: str | None = None
    required: bool = False

    def __post_init__(self) -> None:
        name = self.name.strip().casefold()
        if not _VARIABLE_ID.fullmatch(name):
            raise ExecutionTemplateError("template variable names must be safe identifiers")
        if self.required and self.default is not None:
            raise ExecutionTemplateError(
                f"template variable {name!r} cannot be required and have a default"
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class ExecutionTemplate:
    """Immutable reusable collection of campaign actions."""

    template_id: str
    name: str
    description: str = ""
    actions: tuple[Action, ...] = ()
    variables: tuple[TemplateVariable, ...] = ()
    milestones: tuple[str, ...] = ()
    action_specs: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        template_id = self.template_id.strip().casefold()
        name = self.name.strip()
        description = self.description.strip()
        milestones = tuple(milestone.strip().casefold() for milestone in self.milestones)

        if not _TEMPLATE_ID.fullmatch(template_id):
            raise ExecutionTemplateError("template_id must be a path-safe identifier")
        if not name:
            raise ExecutionTemplateError("name must be a non-empty string")
        action_ids = [action.action_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ExecutionTemplateError("template action ids must be unique")
        variable_names = [variable.name for variable in self.variables]
        if len(variable_names) != len(set(variable_names)):
            raise ExecutionTemplateError("template variable names must be unique")
        if len(milestones) != len(set(milestones)):
            raise ExecutionTemplateError("template milestone names must be unique")
        if any(not _VARIABLE_ID.fullmatch(milestone) for milestone in milestones):
            raise ExecutionTemplateError("template milestone names must be safe identifiers")
        collisions = sorted(set(variable_names) & set(milestones))
        if collisions:
            raise ExecutionTemplateError(
                f"template variables and milestones cannot share names: {', '.join(collisions)}"
            )

        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "milestones", milestones)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionTemplate":
        """Build an execution template from parsed YAML."""
        if not isinstance(data, dict):
            raise ExecutionTemplateError("execution template must be a mapping")

        template_id = data.get("id")
        name = data.get("name")
        description = data.get("description", "")
        raw_actions = data.get("actions", [])
        raw_variables = data.get("variables", {})
        raw_milestones = data.get("milestones", [])

        if not isinstance(template_id, str):
            raise ExecutionTemplateError("template.id is required")
        if not isinstance(name, str):
            raise ExecutionTemplateError("template.name is required")
        if not isinstance(description, str):
            raise ExecutionTemplateError("template.description must be a string")
        if not isinstance(raw_actions, list):
            raise ExecutionTemplateError("template.actions must be a list")
        if not isinstance(raw_variables, dict):
            raise ExecutionTemplateError("template.variables must be a mapping")
        if not isinstance(raw_milestones, list) or not all(
            isinstance(item, str) for item in raw_milestones
        ):
            raise ExecutionTemplateError("template.milestones must be a list of strings")

        variables = tuple(
            _parse_variable(variable_name, definition)
            for variable_name, definition in raw_variables.items()
        )
        has_placeholders = _contains_placeholder(raw_actions)

        if has_placeholders:
            action_specs = tuple(_copy_action_spec(item) for item in raw_actions)
            actions: tuple[Action, ...] = ()
        else:
            action_specs = ()
            try:
                actions = tuple(Action.from_dict(item) for item in raw_actions)
            except ActionError as exc:
                raise ExecutionTemplateError(f"invalid template action: {exc}") from exc

        template = cls(
            template_id=template_id,
            name=name,
            description=description,
            actions=actions,
            variables=variables,
            milestones=tuple(raw_milestones),
            action_specs=action_specs,
        )
        template._validate_placeholders()
        return template

    def render_actions(
        self,
        values: dict[str, str] | None = None,
        milestones: dict[str, date] | None = None,
    ) -> tuple[Action, ...]:
        """Render variables and campaign milestones into validated Action objects."""
        supplied_values = values or {}
        resolved_variables = self._resolve_variables(supplied_values)
        resolved_milestones = self._resolve_milestones(milestones or {})
        resolved = {**resolved_variables, **resolved_milestones}

        if not self.action_specs:
            return self.actions

        rendered_specs = tuple(_render_value(spec, resolved) for spec in self.action_specs)
        try:
            return tuple(Action.from_dict(spec) for spec in rendered_specs)
        except ActionError as exc:
            raise ExecutionTemplateError(f"invalid rendered template action: {exc}") from exc

    def _resolve_variables(self, supplied: dict[str, str]) -> dict[str, str]:
        known = {variable.name: variable for variable in self.variables}
        unknown = sorted(set(supplied) - set(known))
        if unknown:
            raise ExecutionTemplateError(f"unknown template variables: {', '.join(unknown)}")

        resolved: dict[str, str] = {}
        missing: list[str] = []
        for name, variable in known.items():
            if name in supplied:
                resolved[name] = supplied[name]
            elif variable.default is not None:
                resolved[name] = variable.default
            elif variable.required:
                missing.append(name)
        if missing:
            raise ExecutionTemplateError(
                f"missing required template variables: {', '.join(sorted(missing))}"
            )
        return resolved

    def _resolve_milestones(self, available: dict[str, date]) -> dict[str, str]:
        missing = sorted(set(self.milestones) - set(available))
        if missing:
            raise ExecutionTemplateError(
                f"campaign is missing required milestones: {', '.join(missing)}"
            )
        return {name: available[name].isoformat() for name in self.milestones}

    def _validate_placeholders(self) -> None:
        if not self.action_specs:
            return
        declared = {variable.name for variable in self.variables} | set(self.milestones)
        referenced = _collect_placeholders(self.action_specs)
        undeclared = sorted(referenced - declared)
        if undeclared:
            raise ExecutionTemplateError(f"undeclared template values: {', '.join(undeclared)}")


def _parse_variable(name: str, definition: Any) -> TemplateVariable:
    if not isinstance(name, str):
        raise ExecutionTemplateError("template variable names must be strings")
    if definition is None:
        return TemplateVariable(name=name, required=True)
    if isinstance(definition, str):
        return TemplateVariable(name=name, default=definition)
    if not isinstance(definition, dict):
        raise ExecutionTemplateError(f"template variable {name!r} must be a mapping")

    description = definition.get("description", "")
    default = definition.get("default")
    required = definition.get("required", default is None)
    if not isinstance(description, str):
        raise ExecutionTemplateError(f"template variable {name!r} description must be a string")
    if default is not None and not isinstance(default, str):
        raise ExecutionTemplateError(f"template variable {name!r} default must be a string")
    if not isinstance(required, bool):
        raise ExecutionTemplateError(f"template variable {name!r} required must be boolean")
    return TemplateVariable(
        name=name,
        description=description,
        default=default,
        required=required,
    )


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PLACEHOLDER.search(value))
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    return False


def _collect_placeholders(value: Any) -> set[str]:
    if isinstance(value, str):
        return {match.group(1) for match in _PLACEHOLDER.finditer(value)}
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in value:
            found.update(_collect_placeholders(item))
        return found
    if isinstance(value, dict):
        found = set()
        for item in value.values():
            found.update(_collect_placeholders(item))
        return found
    return set()


def _render_value(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            operator = match.group(2)
            days_text = match.group(3)
            if name not in variables:
                raise ExecutionTemplateError(f"template value {name!r} has no value")
            raw_value = variables[name]
            if operator is None:
                return raw_value
            try:
                anchor = date.fromisoformat(raw_value)
            except ValueError as exc:
                raise ExecutionTemplateError(
                    f"template value {name!r} must be an ISO date for relative scheduling"
                ) from exc
            days = int(days_text)
            delta = timedelta(days=days if operator == "+" else -days)
            return (anchor + delta).isoformat()

        return _PLACEHOLDER.sub(replace, value)
    if isinstance(value, list):
        return [_render_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _render_value(item, variables) for key, item in value.items()}
    return value


def _copy_action_spec(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExecutionTemplateError("template action entries must be mappings")
    return dict(value)
