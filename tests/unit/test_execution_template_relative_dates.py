from datetime import date

import pytest

from models.execution_template import ExecutionTemplate, ExecutionTemplateError


def build_template() -> ExecutionTemplate:
    return ExecutionTemplate.from_dict(
        {
            "id": "launch-plan",
            "name": "Launch Plan",
            "variables": {
                "launch_date": {"required": True},
                "channel": {"default": "social"},
            },
            "actions": [
                {
                    "id": "prepare",
                    "title": "Prepare {{ channel }} creative",
                    "due_date": "{{ launch_date - 14d }}",
                    "channel": "{{ channel }}",
                },
                {
                    "id": "launch",
                    "title": "Launch",
                    "due_date": "{{ launch_date }}",
                    "depends_on": ["prepare"],
                },
                {
                    "id": "review",
                    "title": "Review",
                    "due_date": "{{ launch_date + 3d }}",
                    "depends_on": ["launch"],
                },
            ],
        }
    )


def test_relative_date_offsets_render_around_anchor_date() -> None:
    template = build_template()

    actions = template.render_actions({"launch_date": "2026-09-01"})

    by_id = {action.action_id: action for action in actions}
    assert by_id["prepare"].due_date == date(2026, 8, 18)
    assert by_id["launch"].due_date == date(2026, 9, 1)
    assert by_id["review"].due_date == date(2026, 9, 4)
    assert by_id["prepare"].channel == "social"


def test_relative_date_offsets_support_overridden_channel() -> None:
    template = build_template()

    actions = template.render_actions({"launch_date": "2026-09-01", "channel": "instagram"})

    assert actions[0].title == "Prepare instagram creative"
    assert actions[0].channel == "instagram"


def test_relative_date_offset_rejects_non_iso_anchor() -> None:
    template = build_template()

    with pytest.raises(ExecutionTemplateError, match="must be an ISO date"):
        template.render_actions({"launch_date": "1 September 2026"})


def test_plain_placeholders_remain_backward_compatible() -> None:
    template = ExecutionTemplate.from_dict(
        {
            "id": "simple-plan",
            "name": "Simple Plan",
            "variables": {"channel": {"required": True}},
            "actions": [
                {
                    "id": "publish",
                    "title": "Publish to {{ channel }}",
                    "channel": "{{ channel }}",
                }
            ],
        }
    )

    action = template.render_actions({"channel": "facebook"})[0]

    assert action.title == "Publish to facebook"
    assert action.channel == "facebook"
