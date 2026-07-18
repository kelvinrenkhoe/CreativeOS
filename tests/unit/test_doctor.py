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
