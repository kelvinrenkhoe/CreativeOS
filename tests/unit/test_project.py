from pathlib import Path

import pytest

from core.project import Project

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Headquarters
artist:
  name: Kelvin Rankie
  genre: Afrobeats
repository:
  songs: catalogue/songs
  campaigns: marketing/campaigns
  templates: creative/templates
  assets: creative/assets
  knowledge: knowledge
  media: media
"""


def test_project_discovers_workspace_and_resolves_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "catalogue" / "songs" / "no-break"
    nested.mkdir(parents=True)
    (workspace / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")

    project = Project.discover(nested)

    assert project.root == workspace.resolve()
    assert project.name == "Kelvin Rankie Headquarters"
    assert project.artist == "Kelvin Rankie"
    assert project.genre == "Afrobeats"
    assert project.songs_path == workspace.resolve() / "catalogue/songs"
    assert project.campaigns_path == workspace.resolve() / "marketing/campaigns"
    assert project.templates_path == workspace.resolve() / "creative/templates"


def test_project_rejects_unknown_repository_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    project = Project(workspace)

    with pytest.raises(KeyError, match="Unknown repository path"):
        project.repository_path("unknown")
