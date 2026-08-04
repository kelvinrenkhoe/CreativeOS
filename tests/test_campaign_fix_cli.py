"""CLI tests for safe campaign fix execution."""

from pathlib import Path

import yaml
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
  genre: Afrobeats
repository:
  songs: songs
  campaigns: campaigns
  books: books
  templates: templates
  assets: assets
  knowledge: knowledge
  media: media
"""


def create_workspace(root: Path) -> Path:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in (
        "songs",
        "campaigns",
        "books",
        "templates",
        "assets",
        "knowledge",
        "media",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    campaign = root / "campaigns" / "no-lose-guard"
    campaign.mkdir(parents=True)
    manifest = {
        "name": "No Lose Guard",
        "artist": "Kelvin Rankie",
        "release_date": "2026-09-01",
        "platforms": ["spotify", "instagram"],
        "goals": {"spotify_streams": 100000},
    }
    (campaign / "campaign.yaml").write_text(
        yaml.safe_dump(manifest),
        encoding="utf-8",
    )
    return campaign


def test_fix_command_applies_safe_templates(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "fix", "No Lose Guard"])

    assert result.exit_code == 0
    assert "CreativeOS Campaign Fix" in result.stdout
    assert "Applied" in result.stdout
    assert (tmp_path / "campaigns/no-lose-guard/assets/artwork").is_dir()
    assert (tmp_path / "campaigns/no-lose-guard/assets/videos").is_dir()
    assert (tmp_path / "campaigns/no-lose-guard/schedule/content-calendar.md").is_file()
    assert (tmp_path / "campaigns/no-lose-guard/press/press-release.md").is_file()
    assert (tmp_path / "campaigns/no-lose-guard/radio/stations.csv").is_file()


def test_fix_command_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    first = runner.invoke(app, ["campaign", "fix", "No Lose Guard"])
    second = runner.invoke(app, ["campaign", "fix", "No Lose Guard"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "Already present" in second.stdout


def test_fix_command_skips_manual_configuration(tmp_path: Path, monkeypatch) -> None:
    campaign = create_workspace(tmp_path)
    manifest = yaml.safe_load((campaign / "campaign.yaml").read_text(encoding="utf-8"))
    manifest.pop("release_date")
    original = yaml.safe_dump(manifest)
    (campaign / "campaign.yaml").write_text(original, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "fix", "No Lose Guard"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout
    assert "Release date" in result.stdout
    assert (campaign / "campaign.yaml").read_text(encoding="utf-8") == original


def test_fix_command_requires_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "fix", "No Lose Guard"])

    assert result.exit_code == 1
    assert "CreativeOS workspace not found" in result.stdout
