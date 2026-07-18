"""CreativeOS project representation."""

from pathlib import Path

from core.discovery import ProjectDiscovery


class Project:
    """Represent a CreativeOS workspace."""

    def __init__(
        self,
        root: Path | None = None,
        discovery: ProjectDiscovery | None = None,
    ) -> None:
        self._discovery = discovery or ProjectDiscovery()
        self.root = (
            root.expanduser().resolve()
            if root is not None
            else self._discovery.discover()
        )

    @classmethod
    def discover(cls, start: Path | None = None) -> "Project":
        """Create a project by discovering its workspace root."""
        discovery = ProjectDiscovery()
        return cls(root=discovery.discover(start), discovery=discovery)

    def path(self, *parts: str) -> Path:
        """Return a path relative to the workspace root."""
        return self.root.joinpath(*parts)

    @property
    def songs_path(self) -> Path:
        return self.path("songs")

    @property
    def campaigns_path(self) -> Path:
        return self.path("campaigns")

    @property
    def assets_path(self) -> Path:
        return self.path("assets")

    @property
    def templates_path(self) -> Path:
        return self.path("templates")

    @property
    def knowledge_path(self) -> Path:
        return self.path("knowledge")