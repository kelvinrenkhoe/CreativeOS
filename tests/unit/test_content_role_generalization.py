import pytest

from models.action import Action, ActionError
from models.execution_template import ExecutionTemplate, ExecutionTemplateError


def test_action_accepts_generic_safe_content_role() -> None:
    action = Action("publish", "Publish testimony", content_role="testimony")

    assert action.content_role == "testimony"


def test_action_normalizes_generic_content_role() -> None:
    action = Action("publish", "Publish case study", content_role="Case Study")

    assert action.content_role == "case-study"


def test_action_rejects_unsafe_content_role() -> None:
    with pytest.raises(ActionError, match="safe content role"):
        Action("publish", "Publish", content_role="../../escape")


def test_template_accepts_declared_domain_content_role() -> None:
    template = ExecutionTemplate.from_dict(
        {
            "id": "church-campaign",
            "name": "Church Campaign",
            "content_roles": ["testimony", "event-reminder"],
            "actions": [
                {
                    "id": "publish-testimony",
                    "title": "Publish testimony",
                    "content_role": "testimony",
                }
            ],
        }
    )

    assert template.content_roles == ("testimony", "event-reminder")
    assert template.actions[0].content_role == "testimony"


def test_template_rejects_undeclared_content_role() -> None:
    with pytest.raises(ExecutionTemplateError, match="undeclared template content roles"):
        ExecutionTemplate.from_dict(
            {
                "id": "company-campaign",
                "name": "Company Campaign",
                "content_roles": ["case-study"],
                "actions": [
                    {
                        "id": "publish-demo",
                        "title": "Publish product demo",
                        "content_role": "product-demo",
                    }
                ],
            }
        )
