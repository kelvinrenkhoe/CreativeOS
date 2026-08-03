"""Tests for CreativeOS doctor CLI commands."""

from pathlib import Path

import yaml
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

CONFIG = {
    "version": 1,
    "workspace": {"name": "Kelvin Rankie Universe"},
    "artist": {
        "name": "Kelvin Rankie",
        "genre": "Afrobeats",
        "country": "United Kingdom",
    },
    "repository": {
        "songs": "songs",
        "campaigns": "campaigns",
        "books": "books",
        "templates": "templates",
        "assets": "assets",
        "knowledge": "knowledge",
        "media": "media",
    },
    "releases": {"current": "", "upcoming": "No Lose Guard"},
    "campaigns": {"active": ["no-lose-guard"]},
}


def _create_workspace(tmp_path: Path, *, release_date: str | None = "2026-09-01") -> None:
    (tmp_path / "creativeos.yaml").write_text(
        yaml.safe_dump(CONFIG),
        encoding="utf-8",
    )

    for directory in CONFIG["repository"].values():
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)

    campaign_path = tmp_path / "campaigns" / "no-lose-guard"
    campaign_path.mkdir(parents=True)
    (campaign_path / "campaign.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "No Lose Guard",
                "artist": "Kelvin Rankie",
                "release_date": release_date,
                "platforms": ["spotify", "instagram"],
                "goals": {"spotify_streams": 100000},
            }
        ),
        encoding="utf-8",
    )


def test_campaign_doctor_reports_healthy_with_warnings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["doctor", "--campaign", "No Lose Guard"])

    assert result.exit_code == 0
    assert "CreativeOS Doctor" in result.stdout
    assert "System healthy with warnings" in result.stdout
    assert "Runtime preset" in result.stdout


def test_campaign_doctor_fails_for_missing_release_date(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _create_workspace(tmp_path, release_date=None)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["doctor", "--campaign", "No Lose Guard"])

    assert result.exit_code == 1
    assert "Release date" in result.stdout
    assert "Health checks failed" in result.stdout


def test_campaign_doctor_fails_for_unknown_campaign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["doctor", "--campaign", "Missing Campaign"])

    assert result.exit_code == 1
    assert "Campaign workspace" in result.stdout
    assert "Manifest configuration" in result.stdout


def test_campaign_doctor_fails_for_unknown_preset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "doctor",
            "--campaign",
            "No Lose Guard",
            "--preset",
            "missing",
        ],
    )

    assert result.exit_code == 1
    assert "runtime preset not found: missing" in result.stdout


def test_campaign_doctor_reports_missing_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["doctor", "--campaign", "No Lose Guard"])

    assert result.exit_code == 1
    assert "CreativeOS workspace not found" in result.stdout
