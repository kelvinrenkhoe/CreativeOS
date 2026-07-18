"""Build and persist the disposable CreativeOS repository index."""

import json
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Protocol

from models.content import RepositoryEntity
from models.index import IndexEntry, RepositoryIndex, RepositoryStats
from services.repository import Repository

INDEX_VERSION = "1"


class IndexError(Exception):
    """Base exception for repository index operations."""


class IndexNotFoundError(IndexError):
    """Raised when the repository index does not exist."""


class IndexCorruptedError(IndexError):
    """Raised when the repository index cannot be decoded."""


class IndexVersionError(IndexError):
    """Raised when the repository index uses an unsupported version."""


class IndexValidationError(IndexError):
    """Raised when the repository index contains invalid data."""


class IndexProject(Protocol):
    root: Path


class IndexService:
    """Build, persist, load, and validate a repository index."""

    def __init__(self, project: IndexProject, repository: Repository | None = None) -> None:
        self.project = project
        self.repository = repository or Repository(project, use_index=False)

    @property
    def index_path(self) -> Path:
        """Return the workspace index file path."""
        return self.project.root / ".creativeos" / "index.json"

    def build(self) -> RepositoryIndex:
        """Build an in-memory index from authoritative repository content."""
        grouped_entities = (
            ("song", self.repository.songs()),
            ("campaign", self.repository.campaigns()),
            ("book", self.repository.books()),
            ("asset", self.repository.assets()),
        )
        entries = tuple(
            self._entry(entity_type, entity)
            for entity_type, entities in grouped_entities
            for entity in entities
        )
        stats = RepositoryStats(
            songs=len(grouped_entities[0][1]),
            campaigns=len(grouped_entities[1][1]),
            books=len(grouped_entities[2][1]),
            assets=len(grouped_entities[3][1]),
        )
        index = RepositoryIndex(
            version=INDEX_VERSION,
            generated_at=datetime.now(UTC),
            stats=stats,
            entries=entries,
        )
        self._validate_index(index)
        return index

    def save(self, index: RepositoryIndex) -> None:
        """Validate and save an index as deterministic JSON."""
        self._validate_index(index)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(self._to_dict(index), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def load(self) -> RepositoryIndex:
        """Load and validate the saved repository index."""
        if not self.index_path.is_file():
            raise IndexNotFoundError(f"Repository index not found: {self.index_path}")

        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (JSONDecodeError, UnicodeDecodeError) as error:
            raise IndexCorruptedError(
                f"Repository index is corrupt: {self.index_path}"
            ) from error

        try:
            index = self._from_dict(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise IndexCorruptedError(
                f"Repository index has an invalid structure: {self.index_path}"
            ) from error

        self._validate_index(index)
        return index

    def refresh(self) -> RepositoryIndex:
        """Rebuild and save the repository index."""
        index = self.build()
        self.save(index)
        return index

    def validate(self) -> RepositoryIndex:
        """Load and validate the saved index, returning it when healthy."""
        return self.load()

    def stats(self) -> RepositoryStats:
        """Return statistics from the saved index."""
        return self.load().stats

    def _entry(self, entity_type: str, entity: RepositoryEntity) -> IndexEntry:
        try:
            relative_path = entity.path.relative_to(self.project.root)
        except ValueError as error:
            raise IndexValidationError(
                f"Indexed path is outside the workspace: {entity.path}"
            ) from error
        return IndexEntry(
            entity_type=entity_type,
            slug=entity.slug,
            name=entity.name,
            path=relative_path,
        )

    @staticmethod
    def _to_dict(index: RepositoryIndex) -> dict[str, object]:
        return {
            "version": index.version,
            "generated_at": index.generated_at.isoformat(),
            "stats": {
                "songs": index.stats.songs,
                "campaigns": index.stats.campaigns,
                "books": index.stats.books,
                "assets": index.stats.assets,
            },
            "entries": [
                {
                    "entity_type": entry.entity_type,
                    "slug": entry.slug,
                    "name": entry.name,
                    "path": entry.path.as_posix(),
                }
                for entry in index.entries
            ],
        }

    @staticmethod
    def _from_dict(payload: object) -> RepositoryIndex:
        if not isinstance(payload, dict):
            raise TypeError("Index payload must be an object.")

        stats_payload = payload["stats"]
        entries_payload = payload["entries"]
        if not isinstance(stats_payload, dict) or not isinstance(entries_payload, list):
            raise TypeError("Index statistics and entries have invalid types.")

        return RepositoryIndex(
            version=str(payload["version"]),
            generated_at=datetime.fromisoformat(str(payload["generated_at"])),
            stats=RepositoryStats(
                songs=int(stats_payload["songs"]),
                campaigns=int(stats_payload["campaigns"]),
                books=int(stats_payload["books"]),
                assets=int(stats_payload["assets"]),
            ),
            entries=tuple(
                IndexEntry(
                    entity_type=str(entry["entity_type"]),
                    slug=str(entry["slug"]),
                    name=str(entry["name"]),
                    path=Path(str(entry["path"])),
                )
                for entry in entries_payload
            ),
        )

    @staticmethod
    def _validate_index(index: RepositoryIndex) -> None:
        if index.version != INDEX_VERSION:
            raise IndexVersionError(
                f"Unsupported repository index version: {index.version}"
            )
        if index.generated_at.tzinfo is None:
            raise IndexValidationError("Repository index timestamp must be timezone-aware.")

        allowed_types = {"song", "campaign", "book", "asset"}
        seen: set[tuple[str, str]] = set()
        counts = {entity_type: 0 for entity_type in allowed_types}
        for entry in index.entries:
            if entry.entity_type not in allowed_types:
                raise IndexValidationError(
                    f"Unsupported repository entity type: {entry.entity_type}"
                )
            if entry.path.is_absolute() or ".." in entry.path.parts:
                raise IndexValidationError(
                    f"Index path must be repository-relative: {entry.path}"
                )
            key = (entry.entity_type, entry.slug)
            if key in seen:
                raise IndexValidationError(
                    f"Duplicate index entry: {entry.entity_type}/{entry.slug}"
                )
            seen.add(key)
            counts[entry.entity_type] += 1

        expected = RepositoryStats(
            songs=counts["song"],
            campaigns=counts["campaign"],
            books=counts["book"],
            assets=counts["asset"],
        )
        if index.stats != expected:
            raise IndexValidationError("Repository index statistics do not match entries.")
