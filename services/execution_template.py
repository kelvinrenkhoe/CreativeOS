"""Load, validate, preview, and apply reusable execution templates."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from models.action import Action
from models.execution_template import ExecutionTemplate, ExecutionTemplateError
from services.action_service import ActionService, ActionServiceError

TEMPLATES_DIRECTORY = Path("templates") / "execution"


class ExecutionTemplateServiceError(Exception):
    """Raised when an execution template cannot be safely used."""


@dataclass(frozen=True, slots=True)
class ExecutionTemplatePlan:
    """Validated, dependency-ordered actions ready for preview or apply."""

    template: ExecutionTemplate
    actions: tuple[Action, ...]


class ExecutionTemplateService:
    """Manage repository execution templates for one campaign ActionService."""

    def __init__(self, repository_root: Path, action_service: ActionService) -> None:
        self.repository_root = repository_root.resolve()
        self.templates_root = (self.repository_root / TEMPLATES_DIRECTORY).resolve()
        self.action_service = action_service

    def list(self) -> tuple[ExecutionTemplate, ...]:
        """Return valid execution templates in stable identifier order."""
        if not self.templates_root.is_dir():
            return ()
        templates: list[ExecutionTemplate] = []
        for path in sorted(self.templates_root.glob("*.yaml")):
            templates.append(self._load_path(path, expected_id=path.stem))
        return tuple(templates)

    def load(self, template_id: str) -> ExecutionTemplate:
        """Load one template by safe identifier."""
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
        if not template_id or any(char not in allowed for char in template_id):
            raise ExecutionTemplateServiceError("template id must be a path-safe identifier")
        path = (self.templates_root / f"{template_id}.yaml").resolve()
        if path.parent != self.templates_root:
            raise ExecutionTemplateServiceError(
                "template path escaped execution templates directory"
            )
        if not path.is_file():
            raise ExecutionTemplateServiceError(f"unknown execution template {template_id!r}")
        return self._load_path(path, expected_id=template_id)

    def plan(self, template_id: str) -> ExecutionTemplatePlan:
        """Validate a template against campaign state without writing actions."""
        template = self.load(template_id)
        existing_ids = {action.action_id for action in self.action_service.repository.list()}
        template_ids = {action.action_id for action in template.actions}
        conflicts = sorted(existing_ids & template_ids)
        if conflicts:
            raise ExecutionTemplateServiceError(
                f"campaign already contains template actions: {', '.join(conflicts)}"
            )

        for action in template.actions:
            missing = [
                dependency
                for dependency in action.depends_on
                if dependency not in template_ids and dependency not in existing_ids
            ]
            if missing:
                raise ExecutionTemplateServiceError(
                    f"action {action.action_id!r} has unknown dependencies: {', '.join(missing)}"
                )

        ordered = self._topological_order(template.actions, existing_ids)
        return ExecutionTemplatePlan(template=template, actions=ordered)

    def apply(self, template_id: str) -> tuple[Action, ...]:
        """Apply a fully validated plan through ActionService creation rules."""
        plan = self.plan(template_id)
        created: list[Action] = []
        try:
            for action in plan.actions:
                created.append(self.action_service.create(action))
        except ActionServiceError as exc:
            for action in reversed(created):
                self.action_service.repository.delete(action.action_id)
            raise ExecutionTemplateServiceError(f"template apply failed: {exc}") from exc
        return tuple(created)

    def _load_path(self, path: Path, *, expected_id: str) -> ExecutionTemplate:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            template = ExecutionTemplate.from_dict(raw)
        except OSError as exc:
            raise ExecutionTemplateServiceError(f"unable to read {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ExecutionTemplateServiceError(f"invalid YAML in {path}: {exc}") from exc
        except ExecutionTemplateError as exc:
            raise ExecutionTemplateServiceError(str(exc)) from exc
        if template.template_id != expected_id:
            raise ExecutionTemplateServiceError(
                f"template id {template.template_id!r} does not match filename {expected_id!r}"
            )
        return template

    @staticmethod
    def _topological_order(
        actions: tuple[Action, ...], existing_ids: set[str]
    ) -> tuple[Action, ...]:
        by_id = {action.action_id: action for action in actions}
        visiting: set[str] = set()
        visited: set[str] = set()
        ordered: list[Action] = []

        def visit(action_id: str) -> None:
            if action_id in visiting:
                raise ExecutionTemplateServiceError(
                    f"dependency cycle detected at action {action_id!r}"
                )
            if action_id in visited:
                return
            visiting.add(action_id)
            action = by_id[action_id]
            for dependency in action.depends_on:
                if dependency in existing_ids:
                    continue
                if dependency in by_id:
                    visit(dependency)
            visiting.remove(action_id)
            visited.add(action_id)
            ordered.append(action)

        for action in actions:
            visit(action.action_id)
        return tuple(ordered)
