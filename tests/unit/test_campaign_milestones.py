from datetime import date
from pathlib import Path

import pytest

from models.campaign_context import CampaignContext, CampaignContextError
from models.execution_template import ExecutionTemplate, ExecutionTemplateError
from services.action_repository import ActionRepository
from services.action_service import ActionService
from services.execution_template import ExecutionTemplateService, ExecutionTemplateServiceError


def test_campaign_context_parses_named_milestones() -> None:
    campaign = CampaignContext.from_dict(
        {
            "id": "launch",
            "name": "Launch",
            "milestones": {
                "content_freeze": "2026-08-25",
                "launch": "2026-09-01",
            },
        }
    )

    assert campaign.milestone_dates == {
        "content_freeze": date(2026, 8, 25),
        "launch": date(2026, 9, 1),
    }


def test_campaign_context_rejects_invalid_milestone_name() -> None:
    with pytest.raises(CampaignContextError, match="milestone names"):
        CampaignContext.from_dict(
            {
                "id": "launch",
                "name": "Launch",
                "milestones": {"Content Freeze": "2026-08-25"},
            }
        )


def test_campaign_context_rejects_invalid_milestone_date() -> None:
    with pytest.raises(CampaignContextError, match="ISO date"):
        CampaignContext.from_dict(
            {
                "id": "launch",
                "name": "Launch",
                "milestones": {"launch": "1 September 2026"},
            }
        )


def test_execution_template_renders_campaign_milestones() -> None:
    template = ExecutionTemplate.from_dict(
        {
            "id": "milestone-plan",
            "name": "Milestone Plan",
            "milestones": ["content_freeze", "launch"],
            "actions": [
                {
                    "id": "finalize",
                    "title": "Finalize",
                    "due_date": "{{ content_freeze }}",
                },
                {
                    "id": "publish",
                    "title": "Publish",
                    "due_date": "{{ launch - 1d }}",
                    "depends_on": ["finalize"],
                },
            ],
        }
    )

    actions = template.render_actions(
        milestones={
            "content_freeze": date(2026, 8, 25),
            "launch": date(2026, 9, 1),
        }
    )

    assert actions[0].due_date == date(2026, 8, 25)
    assert actions[1].due_date == date(2026, 8, 31)


def test_execution_template_rejects_missing_campaign_milestone() -> None:
    template = ExecutionTemplate.from_dict(
        {
            "id": "milestone-plan",
            "name": "Milestone Plan",
            "milestones": ["launch"],
            "actions": [{"id": "publish", "title": "Publish", "due_date": "{{ launch }}"}],
        }
    )

    with pytest.raises(ExecutionTemplateError, match="missing required milestones"):
        template.render_actions(milestones={})


def test_execution_template_rejects_undeclared_milestone_reference() -> None:
    with pytest.raises(ExecutionTemplateError, match="undeclared template values"):
        ExecutionTemplate.from_dict(
            {
                "id": "milestone-plan",
                "name": "Milestone Plan",
                "actions": [{"id": "publish", "title": "Publish", "due_date": "{{ launch }}"}],
            }
        )


def test_template_service_uses_campaign_milestones_automatically(tmp_path: Path) -> None:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "campaign" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n", encoding="utf-8"
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "campaign"
    (project_root / "project.yaml").write_text("id: campaign\nname: Campaign\n", encoding="utf-8")
    (campaign_root / "campaign.yaml").write_text(
        """id: launch
name: Launch
milestones:
  launch: 2026-09-01
""",
        encoding="utf-8",
    )
    template_root = tmp_path / "templates" / "execution"
    template_root.mkdir(parents=True)
    (template_root / "milestone-plan.yaml").write_text(
        """id: milestone-plan
name: Milestone Plan
milestones:
  - launch
actions:
  - id: publish
    title: Publish
    due_date: "{{ launch - 1d }}"
""",
        encoding="utf-8",
    )

    repository = ActionRepository(tmp_path, "kre", "campaign", "launch")
    service = ExecutionTemplateService(tmp_path, ActionService(repository))

    plan = service.plan("milestone-plan")

    assert plan.actions[0].due_date == date(2026, 8, 31)
    assert repository.list() == ()


def test_template_service_reports_missing_campaign_milestone(tmp_path: Path) -> None:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "campaign" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n", encoding="utf-8"
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "campaign"
    (project_root / "project.yaml").write_text("id: campaign\nname: Campaign\n", encoding="utf-8")
    (campaign_root / "campaign.yaml").write_text("id: launch\nname: Launch\n", encoding="utf-8")
    template_root = tmp_path / "templates" / "execution"
    template_root.mkdir(parents=True)
    (template_root / "milestone-plan.yaml").write_text(
        """id: milestone-plan
name: Milestone Plan
milestones:
  - launch
actions:
  - id: publish
    title: Publish
    due_date: "{{ launch }}"
""",
        encoding="utf-8",
    )

    repository = ActionRepository(tmp_path, "kre", "campaign", "launch")
    service = ExecutionTemplateService(tmp_path, ActionService(repository))

    with pytest.raises(ExecutionTemplateServiceError, match="missing required milestones"):
        service.plan("milestone-plan")
