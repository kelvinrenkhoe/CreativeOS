from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
  genre: Afrobeats
repository:
  songs: songs
  campaigns: campaigns
  books: books
  templates: templates
  assets: assets
  knowledge: knowledge
  media: media
"""


def create_workspace(root: Path) -> None:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    (root / "songs" / "Carry Your Name").mkdir(parents=True)
    (root / "campaigns" / "Now Them Go Hear Me").mkdir(parents=True)
    (root / "books" / "Between Hope and Drowning").mkdir(parents=True)
    (root / "assets").mkdir(parents=True)
    (root / "assets" / "cover.png").write_text("asset", encoding="utf-8")


def test_index_build_and_validate_commands(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    build = runner.invoke(app, ["index", "build"])
    validate = runner.invoke(app, ["index", "validate"])

    assert build.exit_code == 0
    assert "Repository Index Built" in build.stdout
    assert (tmp_path / ".creativeos" / "index.json").is_file()
    assert validate.exit_code == 0
    assert "Repository index is healthy" in validate.stdout


def test_search_and_stats_commands(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    search = runner.invoke(app, ["search", "carry"])
    stats = runner.invoke(app, ["stats"])

    assert search.exit_code == 0
    assert "Carry Your Name" in search.stdout
    assert stats.exit_code == 0
    assert "Kelvin Rankie Universe" in stats.stdout
    assert "Songs" in stats.stdout
    assert "4" in stats.stdout
