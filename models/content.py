"""Typed domain models for repository content."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepositoryEntity:
    """Base value object for content discovered in a CreativeOS repository."""

    name: str
    slug: str
    path: Path


@dataclass(frozen=True, slots=True)
class Song(RepositoryEntity):
    """A song workspace discovered in the configured songs directory."""


@dataclass(frozen=True, slots=True)
class Campaign(RepositoryEntity):
    """A campaign workspace discovered in the configured campaigns directory."""


@dataclass(frozen=True, slots=True)
class Book(RepositoryEntity):
    """A book workspace discovered in the configured books directory."""


@dataclass(frozen=True, slots=True)
class Asset(RepositoryEntity):
    """A file or directory discovered in the configured assets directory."""
