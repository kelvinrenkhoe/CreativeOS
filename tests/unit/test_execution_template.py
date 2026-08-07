from pathlib import Path

import pytest

from models.action import Action
from services.action_repository import ActionRepository
from services.action_service import ActionService
from services.execution_template import ExecutionTemplateService, ExecutionTemplateServiceError


def make_campaign(tmp_path: Path) -> ActionRepository:
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
    return ActionRepository(tmp_path, "kre", "campaign", "launch")


def write_template(tmp_path: Path, content: str, name: str = "test-plan") -> None:
    root = tmp_path / "templates" / "execution"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.yaml").write_text(content, encoding="utf-8")


def service(tmp_path: Path) -> tuple[ExecutionTemplateService, ActionRepository]:
    repository = make_campaign(tmp_path)
    return ExecutionTemplateService(tmp_path, ActionService(repository)), repository


def test_plan_orders_dependencies_without_writing(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
actions:
  - id: publish
    title: Publish
    depends_on: [prepare]
  - id: prepare
    title: Prepare
""",
    )

    plan = template_service.plan("test-plan")

    assert [action.action_id for action in plan.actions] == ["prepare", "publish"]
    assert repository.list() == ()


def test_apply_creates_full_plan(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
actions:
  - id: prepare
    title: Prepare
  - id: publish
    title: Publish
    depends_on: [prepare]
""",
    )

    created = template_service.apply("test-plan")

    assert [action.action_id for action in created] == ["prepare", "publish"]
    assert [action.action_id for action in repository.list()] == ["prepare", "publish"]


def test_parameterized_plan_renders_required_date_and_channel(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
variables:
  campaign_date:
    required: true
  channel:
    required: true
actions:
  - id: publish
    title: Publish to {{ channel }}
    due_date: "{{ campaign_date }}"
    channel: "{{ channel }}"
""",
    )

    plan = template_service.plan(
        "test-plan",
        {"campaign_date": "2026-09-01", "channel": "instagram"},
    )

    assert plan.actions[0].title == "Publish to instagram"
    assert plan.actions[0].due_date.isoformat() == "2026-09-01"
    assert plan.actions[0].channel == "instagram"
    assert repository.list() == ()


def test_parameterized_plan_uses_default_variable(tmp_path: Path) -> None:
    template_service, _ = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
variables:
  audience:
    default: supporters
actions:
  - id: define-message
    title: Define message for {{ audience }}
""",
    )

    plan = template_service.plan("test-plan")

    assert plan.actions[0].title == "Define message for supporters"


def test_parameterized_plan_rejects_missing_required_variable(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
variables:
  campaign_date:
    required: true
actions:
  - id: publish
    title: Publish
    due_date: "{{ campaign_date }}"
""",
    )

    with pytest.raises(ExecutionTemplateServiceError, match="missing required"):
        template_service.plan("test-plan")
    assert repository.list() == ()


def test_parameterized_plan_rejects_unknown_variable(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
variables:
  channel:
    default: instagram
actions:
  - id: publish
    title: Publish to {{ channel }}
""",
    )

    with pytest.raises(ExecutionTemplateServiceError, match="unknown template variables"):
        template_service.plan("test-plan", {"unexpected": "value"})
    assert repository.list() == ()


def test_template_rejects_undeclared_placeholder(tmp_path: Path) -> None:
    template_service, _ = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
actions:
  - id: publish
    title: Publish to {{ channel }}
""",
    )

    with pytest.raises(ExecutionTemplateServiceError, match="undeclared"):
        template_service.load("test-plan")


def test_parameterized_apply_persists_rendered_actions(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
variables:
  channel:
    required: true
actions:
  - id: prepare
    title: Prepare {{ channel }} content
  - id: publish
    title: Publish {{ channel }} content
    channel: "{{ channel }}"
    depends_on: [prepare]
""",
    )

    created = template_service.apply("test-plan", {"channel": "facebook"})

    assert [action.action_id for action in created] == ["prepare", "publish"]
    assert repository.load("publish").channel == "facebook"


def test_plan_rejects_existing_action_conflict(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    repository.save(Action("prepare", "Existing Prepare"))
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
actions:
  - id: prepare
    title: Prepare
""",
    )

    with pytest.raises(ExecutionTemplateServiceError, match="already contains"):
        template_service.plan("test-plan")


def test_plan_rejects_unknown_dependency_before_writing(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
actions:
  - id: publish
    title: Publish
    depends_on: [missing]
""",
    )

    with pytest.raises(ExecutionTemplateServiceError, match="unknown dependencies"):
        template_service.plan("test-plan")
    assert repository.list() == ()


def test_plan_rejects_dependency_cycle(tmp_path: Path) -> None:
    template_service, repository = service(tmp_path)
    write_template(
        tmp_path,
        """id: test-plan
name: Test Plan
actions:
  - id: first
    title: First
    depends_on: [second]
  - id: second
    title: Second
    depends_on: [first]
""",
    )

    with pytest.raises(ExecutionTemplateServiceError, match="cycle"):
        template_service.plan("test-plan")
    assert repository.list() == ()


def test_load_rejects_path_traversal(tmp_path: Path) -> None:
    template_service, _ = service(tmp_path)

    with pytest.raises(ExecutionTemplateServiceError, match="path-safe"):
        template_service.load("../escape")
