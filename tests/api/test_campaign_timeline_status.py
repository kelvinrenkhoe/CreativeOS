"""Tests for deterministic campaign timeline lifecycle status."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

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

MANIFEST = """
name: No Lose Guard
artist: Kelvin Rankie
release_date: 2026-09-01
"""


def create_workspace(root: Path, manifest: str = MANIFEST) -> Project:
    """Create a minimum campaign workspace for status API tests."""
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    campaign = root / "campaigns" / "no-lose-guard"
    campaign.mkdir()
    (campaign / "campaign.yaml").write_text(manifest, encoding="utf-8")
    return Project(root)


def test_status_reports_planning_before_campaign_start(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 8, 1),
    )

    assert result.successful
    assert result.current_phase == "Planning"
    assert result.days_elapsed == 0
    assert result.percent_complete == 0
    assert result.current_milestone is None
    assert result.next_milestone == "Pre-save campaign begins"


def test_status_reports_pre_save_phase(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 8, 11),
    )

    assert result.current_phase == "Pre-save"
    assert result.current_milestone == "Pre-save campaign begins"
    assert result.next_milestone == "First teaser video"


def test_status_reports_promotion_phase(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 8, 25),
    )

    assert result.current_phase == "Promotion"
    assert result.current_milestone == "Cover artwork reveal"
    assert result.next_milestone == "Countdown starts"


def test_status_reports_release_week(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 9, 1),
    )

    assert result.current_phase == "Release Week"
    assert result.current_milestone == "Release day"
    assert result.next_milestone == "Thank supporters"


def test_status_reports_post_release_phase(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 9, 5),
    )

    assert result.current_phase == "Post Release"
    assert result.current_milestone == "Performance clip"
    assert result.next_milestone == "Playlist push"


def test_status_reports_completed_campaign(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 9, 20),
    )

    assert result.current_phase == "Completed"
    assert result.percent_complete == 100
    assert result.days_remaining == 0
    assert result.next_milestone is None


def test_status_calculates_duration_and_progress(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 8, 25),
    )

    assert result.campaign_start == date(2026, 8, 11)
    assert result.campaign_end == date(2026, 9, 8)
    assert result.duration_days == 29
    assert result.days_elapsed == 15
    assert result.days_remaining == 14
    assert result.percent_complete == 52


def test_status_counts_elapsed_milestones_with_warning(tmp_path: Path) -> None:
    result = CampaignTimelineAPI(create_workspace(tmp_path)).status(
        "No Lose Guard",
        today=date(2026, 8, 26),
    )

    assert result.overdue_milestones == 4
    assert "completion is not tracked" in result.warnings[0]


def test_status_reports_unknown_campaign(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    result = CampaignTimelineAPI(project).status(
        "Missing Campaign",
        today=date(2026, 8, 4),
    )

    assert not result.successful
    assert "Campaign workspace not found" in result.errors[0]


def test_status_reports_invalid_release_date(tmp_path: Path) -> None:
    project = create_workspace(
        tmp_path,
        manifest="name: No Lose Guard\nartist: Kelvin Rankie\nrelease_date: invalid\n",
    )

    result = CampaignTimelineAPI(project).status(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert not result.successful
    assert "Invalid release date" in result.errors[0]


def test_status_reports_empty_generated_timeline(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    service = SimpleNamespace(
        generate=lambda _release_date: SimpleNamespace(
            release_date=date(2026, 9, 1),
            campaign_type="music-release",
            events=(),
        )
    )

    result = CampaignTimelineAPI(project, service=service).status(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert not result.successful
    assert result.errors == ("Campaign timeline contains no milestones",)
