from pathlib import Path

import pytest

from models.content import Asset, Book, Campaign, Song
from services.repository import DuplicateEntityError, EntityNotFoundError, Repository, slugify


class StubProject:
    def __init__(self, root: Path) -> None:
        self.songs_path = root / "songs"
        self.campaigns_path = root / "campaigns"
        self.books_path = root / "books"
        self.assets_path = root / "assets"


def test_slugify_normalizes_human_readable_names() -> None:
    assert slugify("Now Them Go Hear Me") == "now-them-go-hear-me"
    assert slugify("Carry_Your.Name") == "carry-your-name"


def test_repository_discovers_typed_entities(tmp_path: Path) -> None:
    project = StubProject(tmp_path)
    (project.songs_path / "Na You").mkdir(parents=True)
    (project.campaigns_path / "Carry Your Name").mkdir(parents=True)
    (project.books_path / "Between Hope and Drowning").mkdir(parents=True)
    project.assets_path.mkdir(parents=True)
    (project.assets_path / "cover.png").write_text("asset", encoding="utf-8")

    repository = Repository(project)

    assert repository.songs() == (
        Song(name="Na You", slug="na-you", path=project.songs_path / "Na You"),
    )
    assert isinstance(repository.campaign("carry-your-name"), Campaign)
    assert isinstance(repository.book("Between Hope and Drowning"), Book)
    assert isinstance(repository.asset("cover"), Asset)


def test_repository_returns_empty_collections_for_missing_directories(tmp_path: Path) -> None:
    repository = Repository(StubProject(tmp_path))

    assert repository.songs() == ()
    assert repository.campaigns() == ()
    assert repository.books() == ()
    assert repository.assets() == ()


def test_repository_raises_clear_error_for_missing_entity(tmp_path: Path) -> None:
    project = StubProject(tmp_path)
    project.songs_path.mkdir()

    with pytest.raises(EntityNotFoundError, match="Unknown song: Missing Song"):
        Repository(project).song("Missing Song")


def test_repository_rejects_duplicate_slugs(tmp_path: Path) -> None:
    project = StubProject(tmp_path)
    project.assets_path.mkdir(parents=True)
    (project.assets_path / "cover.png").write_text("one", encoding="utf-8")
    (project.assets_path / "cover.jpg").write_text("two", encoding="utf-8")

    with pytest.raises(DuplicateEntityError, match="Duplicate repository entity slug: cover"):
        Repository(project).assets()
