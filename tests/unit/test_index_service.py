import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from models.index import IndexEntry, RepositoryIndex, RepositoryStats
from services.index import (
    INDEX_VERSION,
    IndexCorruptedError,
    IndexNotFoundError,
    IndexService,
    IndexValidationError,
    IndexVersionError,
)


class StubProject:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.songs_path = root / "songs"
        self.campaigns_path = root / "campaigns"
        self.books_path = root / "books"
        self.assets_path = root / "assets"


def create_workspace(project: StubProject) -> None:
    (project.songs_path / "Carry Your Name").mkdir(parents=True)
    (project.campaigns_path / "Now Them Go Hear Me").mkdir(parents=True)
    (project.books_path / "Between Hope and Drowning").mkdir(parents=True)
    project.assets_path.mkdir(parents=True)
    (project.assets_path / "cover.png").write_text("asset", encoding="utf-8")


def test_build_creates_deterministic_typed_index(tmp_path: Path) -> None:
    project = StubProject(tmp_path)
    create_workspace(project)

    index = IndexService(project).build()

    assert index.version == INDEX_VERSION
    assert index.generated_at.tzinfo is UTC
    assert index.stats == RepositoryStats(songs=1, campaigns=1, books=1, assets=1)
    assert [(entry.entity_type, entry.slug) for entry in index.entries] == [
        ("song", "carry-your-name"),
        ("campaign", "now-them-go-hear-me"),
        ("book", "between-hope-and-drowning"),
        ("asset", "cover"),
    ]
    assert all(not entry.path.is_absolute() for entry in index.entries)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    project = StubProject(tmp_path)
    create_workspace(project)
    service = IndexService(project)
    index = service.build()

    service.save(index)

    assert service.index_path == tmp_path / ".creativeos" / "index.json"
    assert service.load() == index


def test_refresh_rebuilds_and_persists_index(tmp_path: Path) -> None:
    project = StubProject(tmp_path)
    create_workspace(project)
    service = IndexService(project)

    index = service.refresh()

    assert service.index_path.is_file()
    assert service.stats() == index.stats
    assert service.validate() == index


def test_load_raises_when_index_is_missing(tmp_path: Path) -> None:
    with pytest.raises(IndexNotFoundError, match="Repository index not found"):
        IndexService(StubProject(tmp_path)).load()


def test_load_rejects_corrupt_json(tmp_path: Path) -> None:
    service = IndexService(StubProject(tmp_path))
    service.index_path.parent.mkdir()
    service.index_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(IndexCorruptedError, match="Repository index is corrupt"):
        service.load()


def test_load_rejects_unsupported_version(tmp_path: Path) -> None:
    service = IndexService(StubProject(tmp_path))
    service.index_path.parent.mkdir()
    service.index_path.write_text(
        json.dumps(
            {
                "version": "999",
                "generated_at": datetime.now(UTC).isoformat(),
                "stats": {"songs": 0, "campaigns": 0, "books": 0, "assets": 0},
                "entries": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(IndexVersionError, match="Unsupported repository index version"):
        service.load()


def test_save_rejects_statistics_that_do_not_match_entries(tmp_path: Path) -> None:
    index = RepositoryIndex(
        version=INDEX_VERSION,
        generated_at=datetime.now(UTC),
        stats=RepositoryStats(songs=2),
        entries=(
            IndexEntry(
                entity_type="song",
                slug="carry-your-name",
                name="Carry Your Name",
                path=Path("songs/Carry Your Name"),
            ),
        ),
    )

    with pytest.raises(IndexValidationError, match="statistics do not match entries"):
        IndexService(StubProject(tmp_path)).save(index)


def test_save_rejects_duplicate_entries(tmp_path: Path) -> None:
    entry = IndexEntry(
        entity_type="song",
        slug="carry-your-name",
        name="Carry Your Name",
        path=Path("songs/Carry Your Name"),
    )
    index = RepositoryIndex(
        version=INDEX_VERSION,
        generated_at=datetime.now(UTC),
        stats=RepositoryStats(songs=2),
        entries=(entry, entry),
    )

    with pytest.raises(IndexValidationError, match="Duplicate index entry"):
        IndexService(StubProject(tmp_path)).save(index)
