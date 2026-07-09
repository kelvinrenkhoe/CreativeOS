from pathlib import Path

import pytest

from services.scaffold import ScaffoldError, ScaffoldService


def test_apply_song_scaffold(tmp_path: Path):
    target = tmp_path / "No-Lose-Guard"

    ScaffoldService().apply("song", target)

    assert (target / "audio").is_dir()
    assert (target / "lyrics").is_dir()
    assert (target / "covers").is_dir()
    assert (target / "ai-images").is_dir()
    assert (target / "README.md").is_file()


def test_missing_scaffold_raises_error(tmp_path: Path):
    service = ScaffoldService(scaffold_root=tmp_path)

    with pytest.raises(ScaffoldError):
        service.apply("missing", tmp_path / "target")
