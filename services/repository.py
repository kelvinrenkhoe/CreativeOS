"""Repository discovery and lookup services."""

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar

from models.content import Asset, Book, Campaign, RepositoryEntity, Song
from models.index import IndexEntry, RepositoryIndex, RepositoryStats

if TYPE_CHECKING:
    from services.index import IndexService


class RepositoryProject(Protocol):
    root: Path
    songs_path: Path
    campaigns_path: Path
    books_path: Path
    assets_path: Path


class EntityNotFoundError(LookupError):
    """Raised when a requested repository entity cannot be found."""


class DuplicateEntityError(ValueError):
    """Raised when two repository entries resolve to the same slug."""


EntityT = TypeVar("EntityT", bound=RepositoryEntity)


def slugify(value: str) -> str:
    """Convert a human-readable repository name into a stable lookup slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError("Repository entity names must contain letters or numbers.")
    return slug


class Repository:
    """Discover and query typed content in a CreativeOS workspace."""

    def __init__(self, project: RepositoryProject, *, use_index: bool = True) -> None:
        self.project = project
        self.use_index = use_index
        self._index: IndexService | None = None

    def songs(self) -> tuple[Song, ...]:
        return self._entities("song", Song, self.project.songs_path)

    def campaigns(self) -> tuple[Campaign, ...]:
        return self._entities("campaign", Campaign, self.project.campaigns_path)

    def books(self) -> tuple[Book, ...]:
        return self._entities("book", Book, self.project.books_path)

    def assets(self) -> tuple[Asset, ...]:
        return self._entities(
            "asset",
            Asset,
            self.project.assets_path,
            directories_only=False,
        )

    def song(self, name: str) -> Song:
        return self._find(name, self.songs(), "song")

    def campaign(self, name: str) -> Campaign:
        return self._find(name, self.campaigns(), "campaign")

    def book(self, name: str) -> Book:
        return self._find(name, self.books(), "book")

    def asset(self, name: str) -> Asset:
        return self._find(name, self.assets(), "asset")

    def refresh(self) -> RepositoryIndex:
        """Rebuild and persist the repository index."""
        return self._index_service().refresh()

    def stats(self) -> RepositoryStats:
        """Return statistics from the repository index."""
        return self._load_index().stats

    def search(
        self,
        query: str,
        *,
        entity_type: str | None = None,
    ) -> tuple[RepositoryEntity, ...]:
        """Search indexed entities by name or slug."""
        needle = query.casefold().strip()
        if not needle:
            return ()

        entries = self._load_index().entries
        matches = (
            entry
            for entry in entries
            if (entity_type is None or entry.entity_type == entity_type)
            and (needle in entry.name.casefold() or needle in entry.slug.casefold())
        )
        return tuple(self._materialize(entry) for entry in matches)

    def _entities(
        self,
        entity_type: str,
        factory: Callable[..., EntityT],
        root: Path,
        *,
        directories_only: bool = True,
    ) -> tuple[EntityT, ...]:
        if not self.use_index:
            return self._discover(root, factory, directories_only=directories_only)

        return tuple(
            factory(
                name=entry.name,
                slug=entry.slug,
                path=self.project.root / entry.path,
            )
            for entry in self._load_index().entries
            if entry.entity_type == entity_type
        )

    def _load_index(self) -> RepositoryIndex:
        from services.index import IndexNotFoundError

        service = self._index_service()
        try:
            return service.load()
        except IndexNotFoundError:
            return service.refresh()

    def _index_service(self) -> "IndexService":
        if self._index is None:
            from services.index import IndexService

            self._index = IndexService(self.project)
        return self._index

    def _materialize(self, entry: IndexEntry) -> RepositoryEntity:
        factories: dict[str, type[RepositoryEntity]] = {
            "song": Song,
            "campaign": Campaign,
            "book": Book,
            "asset": Asset,
        }
        factory = factories[entry.entity_type]
        return factory(
            name=entry.name,
            slug=entry.slug,
            path=self.project.root / entry.path,
        )

    @staticmethod
    def _discover(
        root: Path,
        factory: Callable[..., EntityT],
        *,
        directories_only: bool = True,
    ) -> tuple[EntityT, ...]:
        if not root.exists():
            return ()

        entities: list[EntityT] = []
        slugs: set[str] = set()
        for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            if path.name.startswith(".") or (directories_only and not path.is_dir()):
                continue

            name = path.stem if path.is_file() else path.name
            slug = slugify(name)
            if slug in slugs:
                raise DuplicateEntityError(f"Duplicate repository entity slug: {slug}")
            slugs.add(slug)
            entities.append(factory(name=name, slug=slug, path=path))

        return tuple(entities)

    @staticmethod
    def _find(name: str, entities: tuple[EntityT, ...], entity_type: str) -> EntityT:
        requested = slugify(name)
        for entity in entities:
            if entity.slug == requested or entity.name.casefold() == name.casefold():
                return entity
        raise EntityNotFoundError(f"Unknown {entity_type}: {name}")
