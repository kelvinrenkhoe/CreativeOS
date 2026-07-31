"""Tests for the CreativeOS doctor service."""

from pathlib import Path

from services.doctor import (
    REQUIRED_DIRECTORIES,
    REQUIRED_FILES,
    DoctorService,
)


def create_project_structure(root: Path) -> None:
    """Create the minimum CreativeOS project structure."""
    for filename in REQUIRED_FILES:
        (root / filename).touch()

    for directory in REQUIRED_DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)


def test_doctor_detects_required_project_structure(tmp_path: Path) -> None:
    create_project_structure(tmp_path)

    report = DoctorService(root=tmp_path).run()

    project_checks = [
        check
        for check in report.checks
        if check.category in {"Project", "Structure"} and check.name != "Git repository"
    ]

    assert project_checks
    assert all(check.passed for check in project_checks)


def test_doctor_reports_missing_pyproject(tmp_path: Path) -> None:
    create_project_structure(tmp_path)
    (tmp_path / "pyproject.toml").unlink()

    report = DoctorService(root=tmp_path).run()

    pyproject_check = next(check for check in report.checks if check.name == "pyproject.toml")

    assert pyproject_check.passed is False


def test_doctor_reports_missing_directory(tmp_path: Path) -> None:
    create_project_structure(tmp_path)
    (tmp_path / "scaffolds").rmdir()

    report = DoctorService(root=tmp_path).run()

    scaffold_check = next(check for check in report.checks if check.name == "scaffolds/")

    assert scaffold_check.passed is False


WORKSPACE_CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Cinematic Universe
artist:
  name: Kelvin Rankie
  genre: Afrobeats
repository:
  songs: 01_Songs
  campaigns: campaigns
  books: 02_Book
  templates: templates
  assets: assets
  knowledge: knowledge
  media: media
releases:
  current: No Break
  upcoming: No Lose Guard
campaigns:
  active:
    - No Break
    - No Lose Guard
"""


def create_creator_workspace(root: Path) -> None:
    """Create a valid creator workspace for doctor tests."""
    (root / "creativeos.yaml").write_text(WORKSPACE_CONFIG, encoding="utf-8")

    for directory in (
        "01_Songs/No Break",
        "01_Songs/No Lose Guard",
        "campaigns/No Break",
        "campaigns/No Lose Guard",
        "02_Book",
        "templates",
        "assets",
        "knowledge",
        "media",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)


def test_doctor_validates_creator_workspace_from_nested_path(tmp_path: Path) -> None:
    create_creator_workspace(tmp_path)
    nested = tmp_path / "01_Songs" / "No Break"

    report = DoctorService(root=nested).run()

    workspace_checks = [
        check
        for check in report.checks
        if check.category in {"Workspace", "Repository", "Releases", "Campaigns"}
    ]

    assert workspace_checks
    assert all(check.passed for check in workspace_checks)
    assert not any(check.name == "pyproject.toml" for check in report.checks)


def test_doctor_reports_missing_configured_release_directory(
    tmp_path: Path,
) -> None:
    create_creator_workspace(tmp_path)
    (tmp_path / "01_Songs" / "No Lose Guard").rmdir()

    report = DoctorService(root=tmp_path).run()

    upcoming_check = next(
        check
        for check in report.checks
        if check.category == "Releases" and check.name == "Upcoming song"
    )

    assert upcoming_check.passed is False
    assert upcoming_check.detail.endswith("01_Songs/No Lose Guard")


def test_doctor_reports_missing_active_campaign_directory(
    tmp_path: Path,
) -> None:
    create_creator_workspace(tmp_path)
    (tmp_path / "campaigns" / "No Lose Guard").rmdir()

    report = DoctorService(root=tmp_path).run()

    campaign_check = next(
        check
        for check in report.checks
        if check.category == "Campaigns" and check.name == "No Lose Guard"
    )

    assert campaign_check.passed is False
    assert campaign_check.detail.endswith("campaigns/No Lose Guard")
