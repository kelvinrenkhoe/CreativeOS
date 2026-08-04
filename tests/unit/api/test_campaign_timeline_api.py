"""Tests for the structured campaign timeline API."""

from datetime import date
from pathlib import Path

from api.campaign_timeline import CampaignTimelineAPI
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


def create_workspace(root: Path) -> Project:
    """Create the minimum CreativeOS workspace required by API tests."""
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    return Project(root)


def write_manifest(
    project: Project,
    release_date: str | None,
) -> None:
    """Write a campaign manifest with an optional release date."""
    campaign = project.campaigns_path / "no-lose-guard"
    campaign.mkdir(parents=True, exist_ok=True)
    release_line = f"release_date: {release_date}\n" if release_date is not None else ""
    campaign.joinpath("campaign.yaml").write_text(
        "name: No Lose Guard\n"
        "artist: Kelvin Rankie\n"
        f"{release_line}"
        "platforms: [spotify, instagram]\n"
        "goals: [awareness]\n",
        encoding="utf-8",
    )


def test_timeline_returns_structured_chronological_events(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    write_manifest(project, "2026-09-01")

    result = CampaignTimelineAPI(project).timeline("No Lose Guard")

    assert result.successful
    assert result.campaign == "No Lose Guard"
    assert result.release_date == date(2026, 9, 1)
    assert not result.warnings
    assert not result.errors
    assert result.timeline_events
    assert tuple(event.date for event in result.timeline_events) == tuple(
        sorted(event.date for event in result.timeline_events)
    )
    assert any(event.day_offset == 0 for event in result.timeline_events)


def test_timeline_returns_missing_campaign_error(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    result = CampaignTimelineAPI(project).timeline("Missing Campaign")

    assert not result.successful
    assert result.release_date is None
    assert not result.timeline_events
    assert "Campaign workspace not found" in result.errors[0]
    assert 'creativeos campaign create "Missing Campaign"' in result.errors[0]


def test_timeline_returns_missing_release_date_error(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    write_manifest(project, None)

    result = CampaignTimelineAPI(project).timeline("No Lose Guard")

    assert not result.successful
    assert "Release date is not configured" in result.errors[0]
    assert "campaign.yaml" in result.errors[0]


def test_timeline_returns_invalid_release_date_error(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    write_manifest(project, "September-1-2026")

    result = CampaignTimelineAPI(project).timeline("No Lose Guard")

    assert not result.successful
    assert "Invalid release date" in result.errors[0]
    assert "YYYY-MM-DD" in result.errors[0]


def test_timeline_normalises_yaml_date_values(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    write_manifest(project, "2026-09-01")

    result = CampaignTimelineAPI(project).timeline("No Lose Guard")

    assert result.successful
    assert result.release_date == date(2026, 9, 1)
