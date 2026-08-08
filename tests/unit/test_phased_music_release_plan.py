from datetime import date
from pathlib import Path

from services.action_repository import ActionRepository
from services.action_service import ActionService
from services.execution_template import ExecutionTemplateService


CAMPAIGN = """id: launch
name: No Lose Guard Launch
type: music-release
status: draft
objective: Build release awareness.
start_date: 2026-08-11
end_date: 2026-09-08
channels:
  - instagram
milestones:
  campaign_start: 2026-08-11
  content_freeze: 2026-08-25
  launch: 2026-09-01
  performance_review: 2026-09-08
"""


def make_workspace(tmp_path: Path) -> ExecutionTemplateService:
    project_root = tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard"
    campaign_root = project_root / "campaigns" / "launch"
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n",
        encoding="utf-8",
    )
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\ntype: song\n",
        encoding="utf-8",
    )
    (campaign_root / "campaign.yaml").write_text(CAMPAIGN, encoding="utf-8")

    template_root = tmp_path / "templates" / "execution"
    template_root.mkdir(parents=True)
    source = Path("templates/execution/milestone-campaign.yaml").read_text(encoding="utf-8")
    (template_root / "milestone-campaign.yaml").write_text(source, encoding="utf-8")

    repository = ActionRepository(tmp_path, "kre", "no-lose-guard", "launch")
    return ExecutionTemplateService(tmp_path, ActionService(repository))


def test_phased_music_release_plan_resolves_release_dates(tmp_path: Path) -> None:
    service = make_workspace(tmp_path)

    plan = service.plan("milestone-campaign", {"primary_channel": "instagram"})
    actions = {action.action_id: action for action in plan.actions}

    assert len(actions) == 11
    assert actions["define-rollout-brief"].due_date == date(2026, 8, 11)
    assert actions["plan-content-sequence"].due_date == date(2026, 8, 20)
    assert actions["produce-release-assets"].due_date == date(2026, 8, 23)
    assert actions["finalize-assets"].due_date == date(2026, 8, 25)
    assert actions["schedule-teaser"].due_date == date(2026, 8, 27)
    assert actions["publish-teaser"].due_date == date(2026, 8, 28)
    assert actions["schedule-launch"].due_date == date(2026, 8, 31)
    assert actions["publish-launch"].due_date == date(2026, 9, 1)
    assert actions["publish-follow-up"].due_date == date(2026, 9, 4)
    assert actions["collect-performance-signals"].due_date == date(2026, 9, 7)
    assert actions["review-performance"].due_date == date(2026, 9, 8)


def test_phased_music_release_plan_preserves_dependency_chain(tmp_path: Path) -> None:
    service = make_workspace(tmp_path)

    plan = service.plan("milestone-campaign", {"primary_channel": "instagram"})
    actions = {action.action_id: action for action in plan.actions}

    assert actions["plan-content-sequence"].depends_on == ("define-rollout-brief",)
    assert actions["finalize-assets"].depends_on == ("produce-release-assets",)
    assert actions["publish-teaser"].depends_on == ("schedule-teaser",)
    assert actions["publish-launch"].depends_on == ("schedule-launch",)
    assert actions["review-performance"].depends_on == ("collect-performance-signals",)


def test_phased_music_release_plan_keeps_primary_channel_explicit(tmp_path: Path) -> None:
    service = make_workspace(tmp_path)

    plan = service.plan("milestone-campaign", {"primary_channel": "instagram"})
    channel_actions = tuple(action for action in plan.actions if action.channel)

    assert channel_actions
    assert {action.channel for action in channel_actions} == {"instagram"}
