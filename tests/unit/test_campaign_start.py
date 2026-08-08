from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from services.campaign_context import CampaignContextService
from services.campaign_start import CampaignStartError, CampaignStartService

runner = CliRunner()


def make_project(tmp_path: Path) -> None:
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


def test_campaign_start_plan_derives_music_release_milestones(tmp_path: Path) -> None:
    make_project(tmp_path)
    service = CampaignStartService(tmp_path, "kre", "no-lose-guard")

    plan = service.plan(
        "launch",
        "No Lose Guard Launch",
        date(2026, 9, 1),
        objective="Build release awareness.",
        channels=("instagram", "tiktok", "spotify"),
    )

    assert plan.campaign.campaign_type == "music-release"
    assert plan.campaign.status == "draft"
    assert plan.campaign.start_date == date(2026, 8, 11)
    assert plan.campaign.end_date == date(2026, 9, 8)
    assert plan.campaign.milestone_dates == {
        "campaign_start": date(2026, 8, 11),
        "content_freeze": date(2026, 8, 25),
        "launch": date(2026, 9, 1),
        "performance_review": date(2026, 9, 8),
    }
    assert not plan.destination.exists()


def test_campaign_start_requires_at_least_one_channel(tmp_path: Path) -> None:
    make_project(tmp_path)
    service = CampaignStartService(tmp_path, "kre", "no-lose-guard")

    try:
        service.plan(
            "launch",
            "No Lose Guard Launch",
            date(2026, 9, 1),
            objective="Build release awareness.",
            channels=(),
        )
    except CampaignStartError as exc:
        assert "at least one campaign channel" in str(exc)
    else:
        raise AssertionError("expected CampaignStartError")


def test_campaign_start_apply_persists_scoped_campaign(tmp_path: Path) -> None:
    make_project(tmp_path)
    service = CampaignStartService(tmp_path, "kre", "no-lose-guard")
    plan = service.plan(
        "launch",
        "No Lose Guard Launch",
        date(2026, 9, 1),
        objective="Build release awareness.",
        channels=("instagram", "spotify"),
    )

    created = service.apply(plan)

    assert created.campaign_id == "launch"
    loaded = CampaignContextService(tmp_path, "kre", "no-lose-guard").load("launch")
    assert loaded == created
    assert loaded.milestone_dates["launch"] == date(2026, 9, 1)


def test_campaign_start_cli_previews_without_writing(tmp_path: Path, monkeypatch) -> None:
    make_project(tmp_path)
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
        ],
    )

    assert result.exit_code == 0
    assert "Music Release Campaign Start" in result.stdout
    assert "Planned Milestones" in result.stdout
    assert "2026-09-01" in result.stdout
    assert "No changes written" in result.stdout
    assert not (
        tmp_path
        / "organizations"
        / "kre"
        / "projects"
        / "no-lose-guard"
        / "campaigns"
        / "launch"
    ).exists()


def test_campaign_start_cli_apply_creates_campaign(tmp_path: Path, monkeypatch) -> None:
    make_project(tmp_path)
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
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert "Created campaign" in result.stdout
    loaded = CampaignContextService(tmp_path, "kre", "no-lose-guard").load("launch")
    assert loaded.campaign_type == "music-release"
