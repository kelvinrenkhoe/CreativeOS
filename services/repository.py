"""Repository discovery and lookup services."""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from models.content import Asset, Book, Campaign, RepositoryEntity, Song


class RepositoryProject(Protocol):
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

    def __init__(self, project: RepositoryProject) -> None:
        self.project = project

    def songs(self) -> tuple[Song, ...]:
        return self._discover(self.project.songs_path, Song)

    def campaigns(self) -> tuple[Campaign, ...]:
        return self._discover(self.project.campaigns_path, Campaign)

    def books(self) -> tuple[Book, ...]:
        return self._discover(self.project.books_path, Book)

    def assets(self) -> tuple[Asset, ...]:
        return self._discover(self.project.assets_path, Asset, directories_only=False)

    def song(self, name: str) -> Song:
        return self._find(name, self.songs(), "song")

    def campaign(self, name: str) -> Campaign:
        return self._find(name, self.campaigns(), "campaign")

    def book(self, name: str) -> Book:
        return self._find(name, self.books(), "book")

    def asset(self, name: str) -> Asset:
        return self._find(name, self.assets(), "asset")

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
