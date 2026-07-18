from datetime import UTC, datetime
from pathlib import Path

from models.index import IndexEntry, RepositoryIndex, RepositoryStats


def test_repository_stats_returns_total_entity_count() -> None:
    stats = RepositoryStats(songs=5, campaigns=3, books=1, assets=12)

    assert stats.total == 21


def test_repository_index_preserves_immutable_entries() -> None:
    generated_at = datetime(2026, 7, 18, 9, 0, tzinfo=UTC)
    entry = IndexEntry(
        entity_type="song",
        slug="carry-your-name",
        name="Carry Your Name",
        path=Path("songs/Carry Your Name"),
    )

    index = RepositoryIndex(
        version="1",
        generated_at=generated_at,
        stats=RepositoryStats(songs=1),
        entries=(entry,),
    )

    assert index.version == "1"
    assert index.generated_at == generated_at
    assert index.stats.total == 1
    assert index.entries == (entry,)
