"""Business rules for campaign execution actions."""

from dataclasses import dataclass, replace
from datetime import date

from models.action import Action
from services.action_repository import ActionRepository, ActionRepositoryError


class ActionServiceError(Exception):
    """Raised when an action operation violates execution rules."""


@dataclass(frozen=True, slots=True)
class ActionProgress:
    """Derived progress for one campaign's action set."""

    total: int
    completed: int

    @property
    def remaining(self) -> int:
        return self.total - self.completed

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.completed / self.total) * 100, 1)


class ActionService:
    """Apply lifecycle, scheduling, and dependency rules to campaign actions."""

    def __init__(self, repository: ActionRepository) -> None:
        self.repository = repository

    def create(self, action: Action) -> Action:
        """Create a new action after validating dependencies, milestone, and uniqueness."""
        if self._exists(action.action_id):
            raise ActionServiceError(f"action {action.action_id!r} already exists")
        self._validate_milestone(action)
        self._validate_dependencies(action, include_candidate=True)
        self.repository.save(action)
        return action

    def complete(self, action_id: str) -> Action:
        action = self._load(action_id)
        if action.status == "completed":
            return action
        if action.status in {"cancelled", "blocked"}:
            raise ActionServiceError(
                f"cannot complete action {action.action_id!r} while status is {action.status!r}"
            )
        unmet = self._unmet_dependencies(action)
        if unmet:
            dependencies = ", ".join(unmet)
            raise ActionServiceError(
                f"cannot complete action {action.action_id!r}; unmet dependencies: {dependencies}"
            )
        return self._save_status(action, "completed")

    def block(self, action_id: str) -> Action:
        action = self._load(action_id)
        if action.status == "blocked":
            return action
        if action.status not in {"pending", "in-progress"}:
            raise ActionServiceError(
                f"cannot block action {action.action_id!r} from status {action.status!r}"
            )
        return self._save_status(action, "blocked")

    def unblock(self, action_id: str) -> Action:
        action = self._load(action_id)
        if action.status != "blocked":
            raise ActionServiceError(f"action {action.action_id!r} is not blocked")
        return self._save_status(action, "pending")

    def cancel(self, action_id: str) -> Action:
        action = self._load(action_id)
        if action.status == "cancelled":
            return action
        if action.status == "completed":
            raise ActionServiceError(f"completed action {action.action_id!r} cannot be cancelled")
        return self._save_status(action, "cancelled")

    def reopen(self, action_id: str) -> Action:
        action = self._load(action_id)
        if action.status not in {"completed", "cancelled"}:
            raise ActionServiceError(
                f"action {action.action_id!r} cannot be reopened from status {action.status!r}"
            )
        return self._save_status(action, "pending")

    def ready(self) -> tuple[Action, ...]:
        return tuple(
            action
            for action in self.repository.list()
            if action.status in {"pending", "in-progress"} and not self._unmet_dependencies(action)
        )

    def today(self, on_date: date | None = None) -> tuple[Action, ...]:
        target = on_date or date.today()
        return tuple(
            action
            for action in self.repository.list()
            if action.due_date == target and action.status not in {"completed", "cancelled"}
        )

    def overdue(self, on_date: date | None = None) -> tuple[Action, ...]:
        target = on_date or date.today()
        return tuple(
            action
            for action in self.repository.list()
            if action.due_date is not None
            and action.due_date < target
            and action.status not in {"completed", "cancelled"}
        )

    def progress(self) -> ActionProgress:
        actions = self.repository.list()
        completed = sum(action.completed for action in actions)
        return ActionProgress(total=len(actions), completed=completed)

    def validate(self) -> None:
        actions = self.repository.list()
        by_id = {action.action_id: action for action in actions}
        for action in actions:
            self._validate_milestone(action)
            missing = [dependency for dependency in action.depends_on if dependency not in by_id]
            if missing:
                raise ActionServiceError(
                    f"action {action.action_id!r} has unknown dependencies: {', '.join(missing)}"
                )
        self._reject_cycles(by_id)

    def _validate_milestone(self, action: Action) -> None:
        if action.milestone is None:
            return
        campaign_milestones = {name for name, _ in self.repository.campaign.milestones}
        if action.milestone not in campaign_milestones:
            raise ActionServiceError(
                f"action {action.action_id!r} references unknown campaign milestone "
                f"{action.milestone!r}"
            )

    def _validate_dependencies(self, action: Action, *, include_candidate: bool) -> None:
        actions = list(self.repository.list())
        by_id = {item.action_id: item for item in actions}
        allowed_ids = set(by_id)
        if include_candidate:
            allowed_ids.add(action.action_id)
        missing = [dependency for dependency in action.depends_on if dependency not in allowed_ids]
        if missing:
            raise ActionServiceError(
                f"action {action.action_id!r} has unknown dependencies: {', '.join(missing)}"
            )
        if include_candidate:
            by_id[action.action_id] = action
        self._reject_cycles(by_id)

    def _unmet_dependencies(self, action: Action) -> tuple[str, ...]:
        unmet: list[str] = []
        for dependency in action.depends_on:
            try:
                dependency_action = self.repository.load(dependency)
            except ActionRepositoryError as exc:
                raise ActionServiceError(
                    f"action {action.action_id!r} has unknown dependency {dependency!r}"
                ) from exc
            if not dependency_action.completed:
                unmet.append(dependency)
        return tuple(unmet)

    @staticmethod
    def _reject_cycles(actions: dict[str, Action]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(action_id: str) -> None:
            if action_id in visiting:
                raise ActionServiceError(f"dependency cycle detected at action {action_id!r}")
            if action_id in visited:
                return
            visiting.add(action_id)
            action = actions[action_id]
            for dependency in action.depends_on:
                if dependency in actions:
                    visit(dependency)
            visiting.remove(action_id)
            visited.add(action_id)

        for action_id in actions:
            visit(action_id)

    def _exists(self, action_id: str) -> bool:
        try:
            self.repository.load(action_id)
        except ActionRepositoryError:
            return False
        return True

    def _load(self, action_id: str) -> Action:
        try:
            return self.repository.load(action_id)
        except ActionRepositoryError as exc:
            raise ActionServiceError(str(exc)) from exc

    def _save_status(self, action: Action, status: str) -> Action:
        updated = replace(action, status=status)
        self.repository.save(updated)
        return updated
