"""Tests for CreativeOS workspace discovery."""

from pathlib import Path

import pytest

from core.discovery import ProjectDiscovery, WorkspaceNotFoundError


def test_discovers_workspace_from_root(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()

    result = ProjectDiscovery().discover(tmp_path)

    assert result == tmp_path.resolve()


def test_discovers_workspace_from_nested_directory(tmp_path: Path) -> None:
    (tmp_path / "creativeos.yaml").touch()

    nested = tmp_path / "songs" / "no-lose-guard" / "lyrics"
    nested.mkdir(parents=True)

    result = ProjectDiscovery().discover(nested)

    assert result == tmp_path.resolve()


def test_accepts_file_as_starting_location(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    lyrics_file = tmp_path / "songs" / "na-you" / "lyrics.md"
    lyrics_file.parent.mkdir(parents=True)
    lyrics_file.touch()

    result = ProjectDiscovery().discover(lyrics_file)

    assert result == tmp_path.resolve()


def test_raises_error_outside_workspace(tmp_path: Path) -> None:
    directory = tmp_path / "unrelated"
    directory.mkdir()

    with pytest.raises(WorkspaceNotFoundError):
        ProjectDiscovery().discover(directory)


def test_nearest_workspace_marker_wins(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()

    nested_workspace = tmp_path / "projects" / "album"
    nested_workspace.mkdir(parents=True)
    (nested_workspace / "creativeos.yaml").touch()

    deep_directory = nested_workspace / "songs" / "demo"
    deep_directory.mkdir(parents=True)

    result = ProjectDiscovery().discover(deep_directory)

    assert result == nested_workspace.resolve()
