from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def make_repository(tmp_path: Path) -> None:
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
        "  launch: 2026-09-01\n",
        encoding="utf-8",
    )
    templates_root = tmp_path / "templates" / "execution"
    templates_root.mkdir(parents=True)
    (templates_root / "milestone-preview.yaml").write_text(
        "id: milestone-preview\n"
        "name: Milestone Preview\n"
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


def test_plan_preview_shows_action_milestones_without_writing(tmp_path: Path, monkeypatch) -> None:
    make_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "execution",
            "plan",
            "preview",
            "milestone-preview",
            "--org",
            "kre",
            "--project",
            "no-lose-guard",
            "--campaign",
            "launch",
        ],
    )

    assert result.exit_code == 0
    assert "Milestone" in result.stdout
    assert "content_freeze" in result.stdout
    assert "launch" in result.stdout
    assert "Finalize assets" in result.stdout
    assert "Publish launch" in result.stdout
    assert "No changes written." in result.stdout
    actions_root = (
        tmp_path
        / "organizations"
        / "kre"
        / "projects"
        / "no-lose-guard"
        / "campaigns"
        / "launch"
        / "actions"
    )
    assert not actions_root.exists()
