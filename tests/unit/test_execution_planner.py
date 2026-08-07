from datetime import date
from pathlib import Path

import pytest

from models.action import Action
from services.action_repository import ActionRepository
from services.action_service import ActionService
from services.execution_planner import ExecutionPlanner


def make_planner(tmp_path: Path) -> tuple[ActionService, ExecutionPlanner]:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n",
        encoding="utf-8",
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard"
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\n",
        encoding="utf-8",
    )
    (campaign_root / "campaign.yaml").write_text(
        "id: launch\nname: Launch\n",
        encoding="utf-8",
    )
    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    service = ActionService(repository)
    return service, ExecutionPlanner(service)


def test_plan_is_empty_when_campaign_has_no_actions(tmp_path: Path) -> None:
    _, planner = make_planner(tmp_path)

    plan = planner.plan(date(2026, 8, 7))

    assert plan.ready == ()
    assert plan.overdue == ()
    assert plan.today == ()
    assert plan.blocked == ()
    assert plan.upcoming == ()
    assert plan.progress.total == 0


def test_plan_groups_actions_by_execution_state(tmp_path: Path) -> None:
    service, planner = make_planner(tmp_path)
    service.create(Action("overdue", "Overdue", due_date=date(2026, 8, 6), priority="high"))
    service.create(Action("today", "Today", due_date=date(2026, 8, 7), priority="normal"))
    service.create(Action("future", "Future", due_date=date(2026, 8, 9), priority="critical"))
    service.create(Action("blocked", "Blocked", due_date=date(2026, 8, 7)))
    service.block("blocked")

    plan = planner.plan(date(2026, 8, 7))

    assert [action.action_id for action in plan.overdue] == ["overdue"]
    assert [action.action_id for action in plan.today] == ["blocked", "today"]
    assert [action.action_id for action in plan.blocked] == ["blocked"]
    assert [action.action_id for action in plan.upcoming] == ["future"]
    assert [action.action_id for action in plan.ready] == ["overdue", "today", "future"]


def test_next_prefers_ready_overdue_then_today_then_other_ready(tmp_path: Path) -> None:
    service, planner = make_planner(tmp_path)
    service.create(Action("future", "Future", due_date=date(2026, 8, 9), priority="critical"))
    service.create(Action("today-low", "Today Low", due_date=date(2026, 8, 7), priority="low"))
    service.create(Action("overdue", "Overdue", due_date=date(2026, 8, 6), priority="normal"))
    service.create(Action("today-high", "Today High", due_date=date(2026, 8, 7), priority="high"))

    actions = planner.next(date(2026, 8, 7), limit=3)

    assert [action.action_id for action in actions] == ["overdue", "today-high", "today-low"]


def test_next_excludes_actions_with_unmet_dependencies(tmp_path: Path) -> None:
    service, planner = make_planner(tmp_path)
    service.create(Action("render-video", "Render Video", due_date=date(2026, 8, 7)))
    service.create(
        Action(
            "publish-video",
            "Publish Video",
            due_date=date(2026, 8, 7),
            priority="critical",
            depends_on=("render-video",),
        )
    )

    actions = planner.next(date(2026, 8, 7), limit=3)

    assert [action.action_id for action in actions] == ["render-video"]


def test_next_uses_priority_then_identifier_for_deterministic_order(tmp_path: Path) -> None:
    service, planner = make_planner(tmp_path)
    service.create(Action("z-normal", "Z", priority="normal"))
    service.create(Action("b-high", "B", priority="high"))
    service.create(Action("a-high", "A", priority="high"))

    actions = planner.next(date(2026, 8, 7), limit=3)

    assert [action.action_id for action in actions] == ["a-high", "b-high", "z-normal"]


def test_next_requires_positive_limit(tmp_path: Path) -> None:
    _, planner = make_planner(tmp_path)

    with pytest.raises(ValueError, match="limit must be at least 1"):
        planner.next(date(2026, 8, 7), limit=0)
