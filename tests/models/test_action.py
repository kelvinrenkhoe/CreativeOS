from datetime import date

import pytest

from models.action import Action, ActionError


def test_action_normalizes_marketing_metadata() -> None:
    action = Action(
        action_id="Instagram Launch",
        title=" Publish launch reel ",
        description=" Release-day hero content ",
        status="In Progress",
        priority="HIGH",
        channel="Instagram",
        depends_on=("Upload Video", "upload-video"),
    )

    assert action.action_id == "instagram-launch"
    assert action.title == "Publish launch reel"
    assert action.description == "Release-day hero content"
    assert action.status == "in-progress"
    assert action.priority == "high"
    assert action.channel == "instagram"
    assert action.depends_on == ("upload-video",)


def test_action_from_dict_parses_due_date() -> None:
    action = Action.from_dict(
        {
            "id": "spotify-canvas",
            "title": "Upload Spotify Canvas",
            "priority": "high",
            "due_date": "2026-09-01",
            "channel": "spotify",
            "depends_on": ["export-canvas"],
        }
    )

    assert action.due_date == date(2026, 9, 1)
    assert action.status == "pending"
    assert action.depends_on == ("export-canvas",)


def test_action_completed_property_reflects_status() -> None:
    assert Action("publish", "Publish", status="completed").completed is True
    assert Action("draft", "Draft").completed is False


@pytest.mark.parametrize("status", ["todo", "done", "waiting"])
def test_action_rejects_unknown_status(status: str) -> None:
    with pytest.raises(ActionError, match="status must be one of"):
        Action("publish", "Publish", status=status)


@pytest.mark.parametrize("priority", ["urgent", "medium", "p1"])
def test_action_rejects_unknown_priority(priority: str) -> None:
    with pytest.raises(ActionError, match="priority must be one of"):
        Action("publish", "Publish", priority=priority)


def test_action_rejects_self_dependency() -> None:
    with pytest.raises(ActionError, match="cannot depend on itself"):
        Action("publish", "Publish", depends_on=("publish",))


def test_action_rejects_path_traversal_identifier() -> None:
    with pytest.raises(ActionError, match="path-safe"):
        Action("../../secrets", "Publish")


def test_action_rejects_invalid_due_date() -> None:
    with pytest.raises(ActionError, match="ISO date"):
        Action.from_dict({"id": "publish", "title": "Publish", "due_date": "tomorrow"})
