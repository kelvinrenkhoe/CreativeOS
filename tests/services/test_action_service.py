from datetime import date
from pathlib import Path

import pytest

from models.action import Action
from services.action_repository import ActionRepository
from services.action_service import ActionService, ActionServiceError


def _write_context(root: Path) -> None:
    organization_root = root / "organizations" / "kre"
    organization_root.mkdir(parents=True)
    (organization_root / "organization.yaml").write_text(
        "id: kre\nname: Kelvin Rankie Entertainment\n",
        encoding="utf-8",
    )
    project_root = organization_root / "projects" / "no-lose-guard"
    project_root.mkdir(parents=True)
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\n",
        encoding="utf-8",
    )
    campaign_root = project_root / "campaigns" / "launch"
    campaign_root.mkdir(parents=True)
    (campaign_root / "campaign.yaml").write_text(
        "id: launch\nname: Launch\nstatus: active\n",
        encoding="utf-8",
    )


def _service(root: Path) -> ActionService:
    _write_context(root)
    repository = ActionRepository(root, "kre", "no-lose-guard", "launch")
    return ActionService(repository)


def test_create_rejects_duplicate_action(tmp_path: Path) -> None:
    service = _service(tmp_path)
    action = Action(action_id="publish-reel", title="Publish Reel")
    service.create(action)

    with pytest.raises(ActionServiceError, match="already exists"):
        service.create(action)


def test_create_rejects_unknown_dependency(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ActionServiceError, match="unknown dependencies"):
        service.create(
            Action(
                action_id="publish-reel",
                title="Publish Reel",
                depends_on=("render-video",),
            )
        )


def test_complete_requires_dependencies(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(Action(action_id="render-video", title="Render Video"))
    service.create(
        Action(
            action_id="publish-reel",
            title="Publish Reel",
            depends_on=("render-video",),
        )
    )

    with pytest.raises(ActionServiceError, match="unmet dependencies"):
        service.complete("publish-reel")

    service.complete("render-video")
    completed = service.complete("publish-reel")

    assert completed.completed is True


def test_block_unblock_cancel_and_reopen(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(Action(action_id="radio-pitch", title="Radio Pitch"))

    blocked = service.block("radio-pitch")
    assert blocked.status == "blocked"

    pending = service.unblock("radio-pitch")
    assert pending.status == "pending"

    cancelled = service.cancel("radio-pitch")
    assert cancelled.status == "cancelled"

    reopened = service.reopen("radio-pitch")
    assert reopened.status == "pending"


def test_today_overdue_ready_and_progress(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(
        Action(
            action_id="yesterday",
            title="Yesterday",
            due_date=date(2026, 8, 6),
        )
    )
    service.create(
        Action(
            action_id="today",
            title="Today",
            due_date=date(2026, 8, 7),
        )
    )
    service.create(
        Action(
            action_id="dependent",
            title="Dependent",
            depends_on=("today",),
        )
    )

    assert [action.action_id for action in service.today(date(2026, 8, 7))] == ["today"]
    assert [action.action_id for action in service.overdue(date(2026, 8, 7))] == ["yesterday"]
    assert [action.action_id for action in service.ready()] == ["today", "yesterday"]

    service.complete("today")
    assert [action.action_id for action in service.ready()] == ["dependent", "yesterday"]

    progress = service.progress()
    assert progress.total == 3
    assert progress.completed == 1
    assert progress.remaining == 2
    assert progress.percent == 33.3


def test_validate_rejects_dependency_cycle(tmp_path: Path) -> None:
    service = _service(tmp_path)
    repository = service.repository
    repository.save(Action(action_id="one", title="One", depends_on=("two",)))
    repository.save(Action(action_id="two", title="Two", depends_on=("one",)))

    with pytest.raises(ActionServiceError, match="dependency cycle"):
        service.validate()
