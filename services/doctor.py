"""Health checks for a CreativeOS installation and project."""

import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from core.config import CONFIG_FILENAME, ConfigurationError
from core.project import Project
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

REPOSITORY_PATHS = (
    "songs",
    "campaigns",
    "books",
    "templates",
    "assets",
    "knowledge",
    "media",
)


class DoctorService:
    """Run health checks against CreativeOS and the current project."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()

    def run(self) -> DoctorReport:
        """Run all health checks and return a report."""
        checks = (
            self._check_python(),
            self._check_package(),
            self._check_git_installed(),
            self._check_git_repository(),
        )

        if self._find_workspace_config() is None:
            checks += (
                *self._check_required_files(),
                *self._check_required_directories(),
            )
        else:
            checks += self._check_creator_workspace()

        return DoctorReport(checks=checks)

    def _find_workspace_config(self) -> Path | None:
        """Return the nearest workspace configuration path."""
        current = self.root.parent if self.root.is_file() else self.root

        for directory in (current, *current.parents):
            config_path = directory / CONFIG_FILENAME
            if config_path.is_file():
                return config_path

        return None

    def _check_creator_workspace(self) -> tuple[DoctorCheck, ...]:
        """Validate the discovered creator workspace."""
        config_path = self._find_workspace_config()
        assert config_path is not None

        config_check = DoctorCheck(
            category="Workspace",
            name=CONFIG_FILENAME,
            passed=True,
            detail=str(config_path),
        )

        try:
            project = Project.discover(self.root)
        except ConfigurationError as exc:
            return (
                config_check,
                DoctorCheck(
                    category="Workspace",
                    name="Configuration",
                    passed=False,
                    detail=str(exc),
                ),
            )

        checks = [
            config_check,
            DoctorCheck(
                category="Workspace",
                name="Configuration",
                passed=True,
                detail=project.name,
            ),
        ]

        checks.extend(
            DoctorCheck(
                category="Repository",
                name=f"{key}/",
                passed=project.repository_path(key).is_dir(),
                detail=str(project.repository_path(key)),
            )
            for key in REPOSITORY_PATHS
        )

        checks.extend(
            self._check_named_directory(
                category="Releases",
                name="Current song",
                parent=project.songs_path,
                configured_name=project.current_song,
            )
        )
        checks.extend(
            self._check_named_directory(
                category="Releases",
                name="Upcoming song",
                parent=project.songs_path,
                configured_name=project.upcoming_song,
            )
        )

        checks.extend(
            DoctorCheck(
                category="Campaigns",
                name=campaign,
                passed=(project.campaigns_path / campaign).is_dir(),
                detail=str(project.campaigns_path / campaign),
            )
            for campaign in project.active_campaigns
        )

        return tuple(checks)

    @staticmethod
    def _check_named_directory(
        *,
        category: str,
        name: str,
        parent: Path,
        configured_name: str,
    ) -> tuple[DoctorCheck, ...]:
        """Validate an optional configured directory."""
        if not configured_name:
            return (
                DoctorCheck(
                    category=category,
                    name=name,
                    passed=True,
                    detail="Not configured",
                ),
            )

        directory = parent / configured_name
        return (
            DoctorCheck(
                category=category,
                name=name,
                passed=directory.is_dir(),
                detail=str(directory),
            ),
        )

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
