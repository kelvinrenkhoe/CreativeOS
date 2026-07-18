from pathlib import Path

import pytest

from core.config import ConfigurationError, find_workspace, load_config

VALID_CONFIG = """
version: 1
workspace:
  name: Test Workspace
artist:
  name: Kelvin
  genre: Afrobeats
repository:
  songs: music/songs
  campaigns: marketing/campaigns
"""


def write_config(workspace: Path, content: str = VALID_CONFIG) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "creativeos.yaml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_find_workspace_from_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_config(workspace)

    assert find_workspace(workspace) == workspace.resolve()


def test_find_workspace_from_nested_directory(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "songs" / "demo" / "lyrics"
    nested.mkdir(parents=True)
    write_config(workspace)

    assert find_workspace(nested) == workspace.resolve()


def test_workspace_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="creativeos.yaml"):
        find_workspace(tmp_path)


def test_load_config_returns_typed_model(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_config(workspace)

    config = load_config(workspace)

    assert config.version == 1
    assert config.workspace.name == "Test Workspace"
    assert config.artist.name == "Kelvin"
    assert config.repository.songs == "music/songs"
    assert config.repository.assets == "assets"


def test_load_config_rejects_missing_required_fields(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_config(workspace, "version: 1\nworkspace: {}\nartist: {}\n")

    with pytest.raises(ConfigurationError, match="workspace.name is required"):
        load_config(workspace)


def test_load_config_rejects_unsupported_version(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_config(
        workspace,
        "version: 2\nworkspace:\n  name: Test\nartist:\n  name: Kelvin\n",
    )

    with pytest.raises(ConfigurationError, match="Expected version: 1"):
        load_config(workspace)


def test_load_config_rejects_invalid_yaml(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_config(workspace, "version: [1\n")

    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_config(workspace)
