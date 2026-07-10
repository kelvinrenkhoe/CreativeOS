from pathlib import Path

import pytest

from services.song import SongError, SongService


def test_create_song(tmp_path: Path) -> None:
    service = SongService()

    song = service.create("No Lose Guard", tmp_path)

    assert song.name == "No Lose Guard"
    assert song.path == tmp_path / "songs" / "No-Lose-Guard"
    assert (song.path / "audio").is_dir()
    assert (song.path / "lyrics").is_dir()
    assert (song.path / "README.md").is_file()


def test_create_song_rejects_empty_name(tmp_path: Path) -> None:
    service = SongService()

    with pytest.raises(SongError, match="cannot be empty"):
        service.create("   ", tmp_path)


def test_create_song_rejects_duplicate(tmp_path: Path) -> None:
    service = SongService()

    service.create("No Lose Guard", tmp_path)

    with pytest.raises(SongError, match="already exists"):
        service.create("No Lose Guard", tmp_path)
