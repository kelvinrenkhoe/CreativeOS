"""Health checks for a CreativeOS installation and project."""

import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from models.doctor import DoctorCheck, DoctorReport

MINIMUM_PYTHON_VERSION = (3, 13)

REQUIRED_FILES = (
    "pyproject.toml",
    "README.md",
)

REQUIRED_DIRECTORIES = (
    "cli",
    "core",
    "models",
    "services",
    "renderers",
    "scaffolds",
    "docs",
    "tests",
)


class DoctorService:
    """Run health checks against a CreativeOS project."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()

    def run(self) -> DoctorReport:
        """Run all health checks and return a report."""
        checks = (
            self._check_python(),
            self._check_package(),
            self._check_git_installed(),
            self._check_git_repository(),
            *self._check_required_files(),
            *self._check_required_directories(),
        )

        return DoctorReport(checks=checks)

    def _check_python(self) -> DoctorCheck:
        current = sys.version_info[:3]
        passed = current >= MINIMUM_PYTHON_VERSION

        required = ".".join(map(str, MINIMUM_PYTHON_VERSION))
        installed = ".".join(map(str, current))

        detail = (
            f"Python {installed}"
            if passed
            else f"Python {installed}; requires Python {required} or newer"
        )

        return DoctorCheck(
            category="Environment",
            name="Python version",
            passed=passed,
            detail=detail,
        )

    def _check_package(self) -> DoctorCheck:
        try:
            package_version = version("creativeos")
        except PackageNotFoundError:
            return DoctorCheck(
                category="Environment",
                name="CreativeOS package",
                passed=False,
                detail="Package is not installed. Run: pip install -e .",
            )

        return DoctorCheck(
            category="Environment",
            name="CreativeOS package",
            passed=True,
            detail=f"Version {package_version}",
        )

    def _check_git_installed(self) -> DoctorCheck:
        git_path = shutil.which("git")

        return DoctorCheck(
            category="Environment",
            name="Git installed",
            passed=git_path is not None,
            detail=git_path or "Git executable was not found",
        )

    def _check_git_repository(self) -> DoctorCheck:
        if shutil.which("git") is None:
            return DoctorCheck(
                category="Project",
                name="Git repository",
                passed=False,
                detail="Cannot check because Git is not installed",
            )

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return DoctorCheck(
                category="Project",
                name="Git repository",
                passed=False,
                detail=str(exc),
            )

        passed = result.returncode == 0 and result.stdout.strip() == "true"

        return DoctorCheck(
            category="Project",
            name="Git repository",
            passed=passed,
            detail=str(self.root) if passed else "Not inside a Git work tree",
        )

    def _check_required_files(self) -> tuple[DoctorCheck, ...]:
        return tuple(
            DoctorCheck(
                category="Project",
                name=filename,
                passed=(self.root / filename).is_file(),
                detail=str(self.root / filename),
            )
            for filename in REQUIRED_FILES
        )

    def _check_required_directories(self) -> tuple[DoctorCheck, ...]:
        return tuple(
            DoctorCheck(
                category="Structure",
                name=f"{directory}/",
                passed=(self.root / directory).is_dir(),
                detail=str(self.root / directory),
            )
            for directory in REQUIRED_DIRECTORIES
        )
