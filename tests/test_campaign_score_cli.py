"""CLI tests for deterministic campaign scoring."""

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
) -> None:
    """Write a campaign manifest for scoring."""
    manifest = {
        "name": "No Lose Guard",
        "artist": "Kelvin Rankie",
        "release_date": release_date,
        "platforms": ["spotify", "instagram"],
        "goals": {"spotify_streams": 100000},
    }

    (campaign / "campaign.yaml").write_text(
        yaml.safe_dump(manifest),
        encoding="utf-8",
    )


def test_campaign_score_command_renders_scores(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "score", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "CreativeOS Campaign Score" in result.stdout
    assert "No Lose Guard" in result.stdout
    assert "Overall score" in result.stdout
    assert "Categories" in result.stdout
    assert "Campaign" in result.stdout
    assert "Runtime" in result.stdout


def test_campaign_score_lists_findings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "score", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "Findings" in result.stdout
    assert "Streaming link" in result.stdout
    assert "Artwork" in result.stdout


def test_low_campaign_score_does_not_fail_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign, release_date=None)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "score", "No Lose Guard"],
    )

    assert result.exit_code == 0
    assert "Release date" in result.stdout
    assert "requires significant improvement" in result.stdout


def test_unknown_campaign_returns_a_score_with_findings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "score", "Missing Campaign"],
    )

    assert result.exit_code == 0
    assert "Missing Campaign" in result.stdout
    assert "Campaign workspace" in result.stdout
    assert "Campaign manifest" in result.stdout


def test_campaign_score_requires_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "score", "No Lose Guard"],
    )

    assert result.exit_code == 1
    assert "CreativeOS workspace not found" in result.stdout
