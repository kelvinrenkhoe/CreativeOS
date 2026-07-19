"""Domain models for the disposable CreativeOS repository index."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """A repository entity recorded in the generated index."""

    entity_type: str
    slug: str
    name: str
    path: Path


@dataclass(frozen=True, slots=True)
class RepositoryStats:
    """Counts of indexed entities grouped by repository type."""

    songs: int = 0
    campaigns: int = 0
    books: int = 0
    assets: int = 0

    @property
    def total(self) -> int:
        """Return the total number of indexed entities."""
        return self.songs + self.campaigns + self.books + self.assets


@dataclass(frozen=True, slots=True)
class RepositoryIndex:
    """A point-in-time, disposable view of repository content."""

    version: str
    generated_at: datetime
    stats: RepositoryStats
    entries: tuple[IndexEntry, ...]
