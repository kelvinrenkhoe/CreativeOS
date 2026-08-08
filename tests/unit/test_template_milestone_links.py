from datetime import date
from pathlib import Path

from models.action import Action
from services.action_repository import ActionRepository
from services.action_service import ActionService
from services.execution_template import ExecutionTemplateService


def make_campaign(tmp_path: Path) -> ActionRepository:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n", encoding="utf-8"
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard"
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\n", encoding="utf-8"
    )
    (campaign_root / "campaign.yaml").write_text(
        "id: launch\n"
        "name: Launch\n"
        "milestones:\n"
        "  content_freeze: 2026-08-25\n"
        "  launch: 2026-09-01\n"
        "  performance_review: 2026-09-08\n",
        encoding="utf-8",
    )
    templates_root = tmp_path / "templates" / "execution"
    templates_root.mkdir(parents=True)
    (templates_root / "milestone-campaign.yaml").write_text(
        "id: milestone-campaign\n"
        "name: Milestone Campaign\n"
        "milestones:\n"
        "  - content_freeze\n"
        "  - launch\n"
        "actions:\n"
        "  - id: finalize-assets\n"
        "    title: Finalize assets\n"
        "    due_date: '{{ content_freeze }}'\n"
        "    milestone: content_freeze\n"
        "  - id: publish-launch\n"
        "    title: Publish launch\n"
        "    due_date: '{{ launch }}'\n"
        "    milestone: launch\n"
        "    depends_on:\n"
        "      - finalize-assets\n",
        encoding="utf-8",
    )
    return ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")


def test_template_preview_preserves_milestone_links(tmp_path: Path) -> None:
    repository = make_campaign(tmp_path)
    service = ExecutionTemplateService(tmp_path, ActionService(repository))

    plan = service.plan("milestone-campaign")

    assert [(action.action_id, action.milestone) for action in plan.actions] == [
        ("finalize-assets", "content_freeze"),
        ("publish-launch", "launch"),
    ]
    assert repository.list() == ()


def test_template_apply_persists_milestone_links(tmp_path: Path) -> None:
    repository = make_campaign(tmp_path)
    service = ExecutionTemplateService(tmp_path, ActionService(repository))

    created = service.apply("milestone-campaign")

    assert [action.milestone for action in created] == ["content_freeze", "launch"]
    assert repository.load("finalize-assets").milestone == "content_freeze"
    assert repository.load("publish-launch").milestone == "launch"
    assert repository.load("publish-launch").due_date == date(2026, 9, 1)
