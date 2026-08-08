from datetime import date
from pathlib import Path

import yaml
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def make_campaign(tmp_path: Path) -> Path:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "release" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n",
        encoding="utf-8",
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "release"
    (project_root / "project.yaml").write_text(
        "id: release\nname: Release\n",
        encoding="utf-8",
    )
    config_path = campaign_root / "campaign.yaml"
    config_path.write_text(
        """id: launch
name: Launch Campaign
type: music-release
status: active
objective: Promote release
channels:
  - instagram
milestones:
  launch: 2026-09-01
""",
        encoding="utf-8",
    )
    return config_path


def args(command: str, *values: str) -> list[str]:
    return [
        "campaign",
        "milestone",
        command,
        *values,
        "--org",
        "kre",
        "--project",
        "release",
        "--campaign",
        "launch",
    ]


def test_milestone_list_shows_stable_dates(tmp_path: Path, monkeypatch) -> None:
    make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("list"))

    assert result.exit_code == 0
    assert "launch" in result.stdout
    assert "2026-09-01" in result.stdout


def test_milestone_set_adds_date_and_preserves_campaign_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("set", "content_freeze", "2026-08-25"))

    assert result.exit_code == 0
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["name"] == "Launch Campaign"
    assert raw["type"] == "music-release"
    assert raw["objective"] == "Promote release"
    assert raw["channels"] == ["instagram"]
    assert raw["milestones"] == {
        "launch": date(2026, 9, 1),
        "content_freeze": date(2026, 8, 25),
    }


def test_milestone_set_updates_existing_date(tmp_path: Path, monkeypatch) -> None:
    config_path = make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("set", "launch", "2026-09-02"))

    assert result.exit_code == 0
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["milestones"]["launch"] == date(2026, 9, 2)


def test_milestone_set_normalizes_identifier_case(tmp_path: Path, monkeypatch) -> None:
    config_path = make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("set", "Performance_Review", "2026-09-08"))

    assert result.exit_code == 0
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["milestones"]["performance_review"] == date(2026, 9, 8)
    assert "Performance_Review" not in raw["milestones"]


def test_milestone_set_rejects_invalid_name_without_writing(tmp_path: Path, monkeypatch) -> None:
    config_path = make_campaign(tmp_path)
    before = config_path.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("set", "Content Freeze", "2026-08-25"))

    assert result.exit_code == 1
    assert "milestone names" in result.stdout
    assert config_path.read_text(encoding="utf-8") == before


def test_milestone_set_rejects_invalid_date_without_writing(tmp_path: Path, monkeypatch) -> None:
    config_path = make_campaign(tmp_path)
    before = config_path.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("set", "content_freeze", "25 August 2026"))

    assert result.exit_code == 1
    assert "ISO date" in result.stdout
    assert config_path.read_text(encoding="utf-8") == before


def test_milestone_remove_deletes_only_requested_date(tmp_path: Path, monkeypatch) -> None:
    config_path = make_campaign(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, args("set", "content_freeze", "2026-08-25"))

    result = runner.invoke(app, args("remove", "content_freeze"))

    assert result.exit_code == 0
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["milestones"] == {"launch": date(2026, 9, 1)}


def test_milestone_remove_unknown_name_is_safe(tmp_path: Path, monkeypatch) -> None:
    config_path = make_campaign(tmp_path)
    before = config_path.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, args("remove", "missing"))

    assert result.exit_code == 1
    assert "unknown campaign milestone" in result.stdout
    assert config_path.read_text(encoding="utf-8") == before


def test_milestone_commands_discover_repository_from_nested_directory(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = make_campaign(tmp_path)
    nested = config_path.parent / "actions" / "drafts"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = runner.invoke(app, args("list"))

    assert result.exit_code == 0
    assert "2026-09-01" in result.stdout
