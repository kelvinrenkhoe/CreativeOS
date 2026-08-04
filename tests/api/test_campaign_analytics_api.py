"""Tests for structured campaign readiness analytics."""

from datetime import date
from pathlib import Path

from api.campaign_analytics import CampaignAnalyticsAPI
from core.project import Project

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
repository:
  songs: songs
  campaigns: campaigns
  assets: assets
  knowledge: knowledge
"""


def create_project(root: Path) -> Project:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    return Project(root)


def write_manifest(root: Path, content: str) -> None:
    campaign = root / "campaigns" / "no-lose-guard"
    campaign.mkdir(parents=True, exist_ok=True)
    campaign.joinpath("campaign.yaml").write_text(content, encoding="utf-8")


def test_summary_returns_ready_campaign_analytics(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    write_manifest(
        tmp_path,
        """name: No Lose Guard
artist: Kelvin Rankie
release_date: 2026-09-01
spotify: https://open.spotify.com/track/example
smart_link: https://example.com/no-lose-guard
hashtags: [NoLoseGuard, KelvinRankie]
platforms: [spotify, instagram, tiktok]
goals:
  spotify_streams: 100000
  playlist_adds: 250
""",
    )

    result = CampaignAnalyticsAPI(project).summary(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert result.successful
    assert result.readiness_score == 100
    assert result.health == "ready"
    assert result.release_date == date(2026, 9, 1)
    assert result.days_to_release == 28
    assert result.platform_count == 3
    assert result.goal_count == 2
    assert result.missing_checks == ()


def test_summary_identifies_missing_campaign_configuration(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    write_manifest(
        tmp_path,
        """name: No Lose Guard
artist: Kelvin Rankie
platforms: [spotify]
goals: {}
""",
    )

    result = CampaignAnalyticsAPI(project).summary("No Lose Guard")

    assert result.successful
    assert result.readiness_score == 17
    assert result.health == "needs-attention"
    assert result.configured_checks == ("platforms",)
    assert result.missing_checks == (
        "release_date",
        "spotify",
        "smart_link",
        "hashtags",
        "goals",
    )


def test_summary_returns_structured_unknown_campaign_error(tmp_path: Path) -> None:
    project = create_project(tmp_path)

    result = CampaignAnalyticsAPI(project).summary("Missing Campaign")

    assert not result.successful
    assert result.readiness_score == 0
    assert "Campaign workspace not found" in result.errors[0]
    assert 'creativeos campaign create "Missing Campaign"' in result.errors[0]


def test_summary_warns_for_invalid_release_date(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    write_manifest(
        tmp_path,
        """name: No Lose Guard
artist: Kelvin Rankie
release_date: September-1-2026
""",
    )

    result = CampaignAnalyticsAPI(project).summary("No Lose Guard")

    assert result.successful
    assert result.release_date is None
    assert result.days_to_release is None
    assert "Invalid release date" in result.warnings[0]


def test_summary_warns_when_release_date_is_past(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    write_manifest(
        tmp_path,
        """name: No Lose Guard
artist: Kelvin Rankie
release_date: 2026-07-01
""",
    )

    result = CampaignAnalyticsAPI(project).summary(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert result.days_to_release == -34
    assert "Campaign release date is in the past" in result.warnings
