import pytest

from models.action import Action, ActionError
from models.execution_template import ExecutionTemplate, ExecutionTemplateError


def test_action_accepts_and_normalizes_generic_content_format() -> None:
    action = Action("publish", "Publish", content_format="Short Video")

    assert action.content_format == "short-video"


def test_action_rejects_unsafe_content_format() -> None:
    with pytest.raises(ActionError, match="safe content format"):
        Action("publish", "Publish", content_format="../../video")


def test_template_accepts_domain_defined_content_format() -> None:
    template = ExecutionTemplate.from_dict(
        {
            "id": "company-campaign",
            "name": "Company Campaign",
            "content_formats": ["product-demo", "case-study"],
            "actions": [
                {
                    "id": "demo",
                    "title": "Demo",
                    "content_format": "product-demo",
                }
            ],
        }
    )

    assert template.content_formats == ("product-demo", "case-study")
    assert template.actions[0].content_format == "product-demo"


def test_template_rejects_undeclared_content_format() -> None:
    with pytest.raises(
        ExecutionTemplateError,
        match="undeclared template content formats",
    ):
        ExecutionTemplate.from_dict(
            {
                "id": "church-campaign",
                "name": "Church Campaign",
                "content_formats": ["sermon-clip"],
                "actions": [
                    {
                        "id": "testimony",
                        "title": "Testimony",
                        "content_format": "testimony-video",
                    }
                ],
            }
        )
