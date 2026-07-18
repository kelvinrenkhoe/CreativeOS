"""Repository-native project abstraction for CreativeOS."""

from pathlib import Path

from core.config import find_workspace, load_config
from models.config import CreativeOSConfig
from models.content import Asset, Book, Campaign, Song
from services.repository import Repository


class Project:
    """Represents a discovered CreativeOS workspace."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = find_workspace(root)
        self.config: CreativeOSConfig = load_config(self.root)
        self._repository = Repository(self)

    @classmethod
    def discover(cls, start_path: Path | None = None) -> "Project":
        """Discover and load the nearest CreativeOS workspace."""
        return cls(start_path)

    @property
    def name(self) -> str:
        return self.config.workspace.name

    @property
    def artist(self) -> str:
        return self.config.artist.name

    @property
    def genre(self) -> str:
        return self.config.artist.genre

    def repository(self) -> Repository:
        """Return the repository service for this workspace."""
        return self._repository

    def songs(self) -> tuple[Song, ...]:
        return self._repository.songs()

    def song(self, name: str) -> Song:
        return self._repository.song(name)

    def campaigns(self) -> tuple[Campaign, ...]:
        return self._repository.campaigns()

    def campaign(self, name: str) -> Campaign:
        return self._repository.campaign(name)

    def books(self) -> tuple[Book, ...]:
        return self._repository.books()

    def book(self, name: str) -> Book:
        return self._repository.book(name)

    def assets(self) -> tuple[Asset, ...]:
        return self._repository.assets()

    def asset(self, name: str) -> Asset:
        return self._repository.asset(name)

    def repository_path(self, key: str) -> Path:
        """Resolve a configured repository directory by name."""
        return self.config.repository_path(self.root, key)

    @property
    def songs_path(self) -> Path:
        return self.repository_path("songs")

    @property
    def campaigns_path(self) -> Path:
        return self.repository_path("campaigns")

    @property
    def books_path(self) -> Path:
        return self.repository_path("books")

    @property
    def templates_path(self) -> Path:
        return self.repository_path("templates")

    @property
    def assets_path(self) -> Path:
        return self.repository_path("assets")

    @property
    def knowledge_path(self) -> Path:
        return self.repository_path("knowledge")

    @property
    def media_path(self) -> Path:
        return self.repository_path("media")
