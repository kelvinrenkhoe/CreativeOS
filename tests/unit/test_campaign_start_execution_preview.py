from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from services.campaign_start import CampaignStartService

runner = CliRunner()

TEMPLATE = """id: milestone-campaign
name: Milestone Campaign
description: Test milestone-aware release execution.
variables:
  primary_channel:
    default: social
actions:
  - id: finalize-assets
    title: Finalize campaign assets
    priority: high
    due_date: "{{ content_freeze }}"
    milestone: content_freeze
  - id: publish-launch
    title: Publish {{ primary_channel }} launch content
    priority: critical
    channel: "{{ primary_channel }}"
    due_date: "{{ launch }}"
    milestone: launch
    depends_on:
      - finalize-assets
  - id: review-performance
    title: Review campaign performance
    due_date: "{{ performance_review }}"
    milestone: performance_review
    depends_on:
      - publish-launch
"""


def make_workspace(tmp_path: Path) -> None:
    project_root = tmp_path / "organizations" / "kre" / "projects" / "no-lose-guard"
    project_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n",
        encoding="utf-8",
    )
    (project_root / "project.yaml").write_text(
        "id: no-lose-guard\nname: No Lose Guard\ntype: song\n",
        encoding="utf-8",
    )
    templates = tmp_path / "templates" / "execution"
    templates.mkdir(parents=True)
    (templates / "milestone-campaign.yaml").write_text(TEMPLATE, encoding="utf-8")


def test_campaign_start_recommends_milestone_execution_template(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    service = CampaignStartService(tmp_path, "kre", "no-lose-guard")

    plan = service.plan(
        "launch",
        "No Lose Guard Launch",
        date(2026, 9, 1),
        objective="Build release awareness.",
        channels=("instagram", "spotify"),
    )

    assert plan.recommended_template_id == "milestone-campaign"
    assert dict(plan.template_variables) == {"primary_channel": "instagram"}


def test_execution_preview_uses_campaign_milestones_without_writing_actions(
    tmp_path: Path,
) -> None:
    make_workspace(tmp_path)
    service = CampaignStartService(tmp_path, "kre", "no-lose-guard")
    plan = service.plan(
        "launch",
        "No Lose Guard Launch",
        date(2026, 9, 1),
        objective="Build release awareness.",
        channels=("instagram", "spotify"),
    )
    service.apply(plan)

    execution = service.preview_execution(plan)

    by_id = {action.action_id: action for action in execution.actions}
    assert by_id["finalize-assets"].due_date == date(2026, 8, 25)
    assert by_id["publish-launch"].due_date == date(2026, 9, 1)
    assert by_id["publish-launch"].channel == "instagram"
    assert by_id["review-performance"].due_date == date(2026, 9, 8)
    assert not (plan.destination / "actions").exists()


def test_campaign_start_apply_renders_execution_preview(tmp_path: Path, monkeypatch) -> None:
    make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "campaign",
            "start",
            "launch",
            "--name",
            "No Lose Guard Launch",
            "--release",
            "2026-09-01",
            "--org",
            "kre",
            "--project",
            "no-lose-guard",
            "--channel",
            "instagram",
            "--channel",
            "spotify",
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert "Recommended Execution Plan Preview" in result.stdout
    assert "Milestone Campaign" in result.stdout
    assert "finalize-assets" in result.stdout
    assert "publish-launch" in result.stdout
    assert "instagram" in result.stdout
    assert "No execution actions written" in result.stdout
