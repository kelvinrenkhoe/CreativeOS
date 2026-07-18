from pathlib import Path

import pytest

from core.config import (
    ConfigurationError,
    find_workspace,
    load_config,
)


def test_find_workspace(tmp_path: Path):
    """
    CreativeOS should discover the workspace.
    """

    workspace = tmp_path / "workspace"

    config = workspace / "creativeos-config"

    config.mkdir(parents=True)

    (config / "project.yaml").write_text(
        """
project:
  name: Test Project
"""
    )

    found = find_workspace(workspace)

    assert found == workspace


def test_workspace_not_found(tmp_path: Path):
    """
    Missing workspace should raise ConfigurationError.
    """

    with pytest.raises(ConfigurationError):
        find_workspace(tmp_path)


def test_load_config(tmp_path: Path):
    """
    Configuration should load correctly.
    """

    workspace = tmp_path / "workspace"

    config = workspace / "creativeos-config"

    config.mkdir(parents=True)

    (config / "project.yaml").write_text(
        """
project:
  name: Test Project
artist:
  name: Kelvin
songs:
  current: Test Song
  upcoming: Next Song
campaigns:
  active: []
"""
    )

    loaded = load_config(workspace)

    assert loaded["project"]["name"] == "Test Project"
