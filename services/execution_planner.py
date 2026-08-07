"""Deterministic planning for campaign execution actions."""

from dataclasses import dataclass
from datetime import date

from models.action import Action
from services.action_service import ActionProgress, ActionService

_PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Derived execution view for one campaign on a given date."""

    ready: tuple[Action, ...]
    overdue: tuple[Action, ...]
    today: tuple[Action, ...]
    blocked: tuple[Action, ...]
    upcoming: tuple[Action, ...]
    progress: ActionProgress


class ExecutionPlanner:
    """Select and order campaign work without mutating execution state."""

    def __init__(self, action_service: ActionService) -> None:
        self.action_service = action_service

    def plan(self, on_date: date | None = None) -> ExecutionPlan:
        """Return a deterministic execution plan for the requested date."""
        target = on_date or date.today()
        self.action_service.validate()

        actions = self.action_service.repository.list()
        ready = self._sort_actions(self.action_service.ready(), target)
        overdue = self._sort_actions(self.action_service.overdue(target), target)
        today = self._sort_actions(self.action_service.today(target), target)
        blocked = self._sort_actions(
            tuple(action for action in actions if action.status == "blocked"),
            target,
        )
        upcoming = self._sort_actions(
            tuple(
                action
                for action in actions
                if action.due_date is not None
                and action.due_date > target
                and action.status not in {"completed", "cancelled", "blocked"}
            ),
            target,
        )

        return ExecutionPlan(
            ready=ready,
            overdue=overdue,
            today=today,
            blocked=blocked,
            upcoming=upcoming,
            progress=self.action_service.progress(),
        )

    def next(self, on_date: date | None = None, *, limit: int = 3) -> tuple[Action, ...]:
        """Return the highest-value ready work for the requested date."""
        if limit < 1:
            raise ValueError("limit must be at least 1")

        target = on_date or date.today()
        plan = self.plan(target)
        ready_by_id = {action.action_id: action for action in plan.ready}

        ordered: list[Action] = []
        seen: set[str] = set()
        for group in (plan.overdue, plan.today, plan.ready):
            for action in group:
                if action.action_id not in ready_by_id or action.action_id in seen:
                    continue
                ordered.append(action)
                seen.add(action.action_id)
                if len(ordered) == limit:
                    return tuple(ordered)

        return tuple(ordered)

    @staticmethod
    def _sort_actions(actions: tuple[Action, ...], target: date) -> tuple[Action, ...]:
        return tuple(sorted(actions, key=lambda action: ExecutionPlanner._sort_key(action, target)))

    @staticmethod
    def _sort_key(action: Action, target: date) -> tuple[int, int, date, str]:
        if action.due_date is None:
            due_rank = 2
            due_date = date.max
        elif action.due_date < target:
            due_rank = 0
            due_date = action.due_date
        elif action.due_date == target:
            due_rank = 1
            due_date = action.due_date
        else:
            due_rank = 2
            due_date = action.due_date

        return (
            due_rank,
            _PRIORITY_ORDER[action.priority],
            due_date,
            action.action_id,
        )
