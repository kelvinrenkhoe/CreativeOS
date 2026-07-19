from pathlib import Path

import pytest

from services.knowledge import KnowledgeService


def test_load_top_level_document(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    (knowledge_dir / "artist.md").write_text(
        "# Artist\n\nKelvin Rankie",
        encoding="utf-8",
    )

    service = KnowledgeService(knowledge_dir)

    assert service.load("artist") == "# Artist\n\nKelvin Rankie"


def test_load_song_document(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    songs_dir = knowledge_dir / "songs"
    songs_dir.mkdir(parents=True)

    (songs_dir / "carry-your-name.md").write_text(
        "# Carry Your Name\n\nA tribute song.",
        encoding="utf-8",
    )

    service = KnowledgeService(knowledge_dir)

    assert service.load_song("carry-your-name") == ("# Carry Your Name\n\nA tribute song.")


def test_document_exists(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    (knowledge_dir / "brand.md").write_text(
        "# Brand Voice",
        encoding="utf-8",
    )

    service = KnowledgeService(knowledge_dir)

    assert service.exists("brand") is True
    assert service.exists("missing") is False


def test_song_document_exists(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    songs_dir = knowledge_dir / "songs"
    songs_dir.mkdir(parents=True)

    (songs_dir / "na-you.md").write_text(
        "# Na You",
        encoding="utf-8",
    )

    service = KnowledgeService(knowledge_dir)

    assert service.song_exists("na-you") is True
    assert service.song_exists("missing") is False


def test_missing_document_raises_file_not_found(tmp_path: Path) -> None:
    service = KnowledgeService(tmp_path / "knowledge")

    with pytest.raises(FileNotFoundError, match="Knowledge document not found"):
        service.load("artist")


def test_missing_song_document_raises_file_not_found(tmp_path: Path) -> None:
    service = KnowledgeService(tmp_path / "knowledge")

    with pytest.raises(FileNotFoundError, match="Knowledge document not found"):
        service.load_song("missing-song")
