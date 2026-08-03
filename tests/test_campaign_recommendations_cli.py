"""CLI tests for deterministic campaign recommendations."""

from pathlib import Path

import yaml
from rich.console import Console
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
    """Create a minimal CreativeOS workspace."""
    (root / "creativeos.yaml").write_text(
        CONFIG,
        encoding="utf-8",
    )

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

    return campaign


def write_manifest(
    campaign: Path,
    *,
    release_date: str | None = "2026-09-01",
    smart_link: str | None = None,
) -> None:
    """Write campaign configuration for recommendation tests."""
    manifest = {
        "name": "No Lose Guard",
        "artist": "Kelvin Rankie",
        "release_date": release_date,
        "smart_link": smart_link,
        "platforms": ["spotify", "instagram"],
        "goals": {"spotify_streams": 100000},
    }

    (campaign / "campaign.yaml").write_text(
        yaml.safe_dump(manifest),
        encoding="utf-8",
    )


def complete_optional_assets(campaign: Path) -> None:
    """Create optional campaign files checked by Campaign Doctor."""
    paths = {
        "assets/artwork/cover.jpg": "artwork",
        "assets/videos/trailer.mp4": "video",
        "schedule/content-calendar.md": "# Calendar\n",
        "press/press-release.md": "# Press release\n",
        "radio/stations.csv": "station,contact,status,notes\nRadio 1,a@example.com,pitched,\n",
    }

    for relative_path, content in paths.items():
        path = campaign / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_recommendations_command_renders_recommendations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "recommendations", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "CreativeOS Campaign Recommendations" in result.stdout
    assert "No Lose Guard" in result.stdout
    assert "Recommendations" in result.stdout
    assert "High impact" in result.stdout
    assert "Artwork" in result.stdout
    assert "Streaming link" in result.stdout


def test_recommendations_show_priority_impact_and_action(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign, release_date=None)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "recommendations", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "Priority" in result.stdout
    assert "Impact" in result.stdout
    assert "Release date" in result.stdout
    assert "High" in result.stdout
    assert "release_date" in result.stdout


def test_recommendations_are_informational(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign, release_date=None)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "recommendations", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "Review the highest-priority recommendations first" in result.stdout


def test_complete_campaign_has_no_recommendations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(
        campaign,
        smart_link="https://example.com/no-lose-guard",
    )
    complete_optional_assets(campaign)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "recommendations", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "No campaign recommendations" in result.stdout
    assert "Recommendations" in result.stdout
    assert "0" in result.stdout


def test_unknown_campaign_returns_workspace_recommendation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "cli.campaign.console",
        Console(width=200),
    )

    result = runner.invoke(
        app,
        ["campaign", "recommendations", "Missing Campaign"],
    )

    assert result.exit_code == 0

    output = " ".join(result.stdout.split())

    assert "Missing Campaign" in output
    assert "Campaign workspace" in output
    assert 'creativeos campaign create "Missing Campaign"' in output


def test_recommendations_require_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "recommendations", "No Lose Guard"],
    )

    assert result.exit_code == 1
    assert "CreativeOS workspace not found" in result.stdout
