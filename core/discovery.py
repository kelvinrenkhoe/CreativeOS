"""Workspace discovery for CreativeOS."""

from pathlib import Path


class WorkspaceNotFoundError(RuntimeError):
    """Raised when CreativeOS cannot locate a workspace root."""


class ProjectDiscovery:
    """Locate the root directory of a CreativeOS workspace."""

    MARKERS = (
        "creativeos.yaml",
        "pyproject.toml",
        ".git",
    )

    def discover(self, start: Path | None = None) -> Path:
        """Find the workspace root by walking up from the start directory."""
        current = (start or Path.cwd()).expanduser().resolve()

        if current.is_file():
            current = current.parent

        for directory in (current, *current.parents):
            if self._is_workspace(directory):
                return directory

        raise WorkspaceNotFoundError(
            f"No CreativeOS workspace found from: {current}"
        )

    def _is_workspace(self, directory: Path) -> bool:
        """Return True when the directory contains a workspace marker."""
        return any((directory / marker).exists() for marker in self.MARKERS)
