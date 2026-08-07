from datetime import date
from pathlib import Path

import pytest

from models.action import Action
from services.action_repository import ActionRepository, ActionRepositoryError


def _write_campaign(root: Path, organization: str, project: str, campaign: str) -> None:
    organization_root = root / "organizations" / organization
    organization_root.mkdir(parents=True, exist_ok=True)
    (organization_root / "organization.yaml").write_text(
        f"id: {organization}\nname: {organization.title()}\n",
        encoding="utf-8",
    )

    project_root = organization_root / "projects" / project
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "project.yaml").write_text(
        f"id: {project}\nname: {project.title()}\n",
        encoding="utf-8",
    )

    campaign_root = project_root / "campaigns" / campaign
    campaign_root.mkdir(parents=True, exist_ok=True)
    (campaign_root / "campaign.yaml").write_text(
        f"id: {campaign}\nname: {campaign.title()}\nstatus: active\n",
        encoding="utf-8",
    )


def test_repository_saves_and_loads_action(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    action = Action(
        action_id="publish-teaser",
        title="Publish teaser",
        description="Publish the approved teaser asset.",
        priority="high",
        due_date=date(2026, 8, 10),
        channel="instagram",
    )

    path = repository.save(action)
    loaded = repository.load("publish-teaser")

    assert path.name == "publish-teaser.yaml"
    assert loaded == action


def test_repository_lists_actions_in_stable_order(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    repository.save(Action(action_id="second-action", title="Second"))
    repository.save(Action(action_id="first-action", title="First"))

    assert [action.action_id for action in repository.list()] == [
        "first-action",
        "second-action",
    ]


def test_repository_isolates_campaign_actions(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    _write_campaign(tmp_path, "kre", "no-lose-guard", "radio")
    launch = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    radio = ActionRepository(tmp_path, "kre", "no-lose-guard", "radio")

    launch.save(Action(action_id="launch-post", title="Launch post"))
    radio.save(Action(action_id="radio-pitch", title="Radio pitch"))

    assert [action.action_id for action in launch.list()] == ["launch-post"]
    assert [action.action_id for action in radio.list()] == ["radio-pitch"]


def test_repository_rejects_action_path_traversal(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")

    with pytest.raises(ActionRepositoryError):
        repository.load("../../secrets")


def test_repository_rejects_filename_id_mismatch(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    repository.actions_root.mkdir(parents=True, exist_ok=True)
    (repository.actions_root / "publish-teaser.yaml").write_text(
        "id: wrong-id\ntitle: Publish teaser\n",
        encoding="utf-8",
    )

    with pytest.raises(ActionRepositoryError, match="does not match filename"):
        repository.load("publish-teaser")


def test_repository_deletes_existing_action(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    repository.save(Action(action_id="publish-teaser", title="Publish teaser"))

    repository.delete("publish-teaser")

    with pytest.raises(ActionRepositoryError, match="unknown action"):
        repository.load("publish-teaser")
