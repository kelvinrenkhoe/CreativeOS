from pathlib import Path

import yaml
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


def test_campaign_create_command(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "create", "Now Them Go Hear Me"])

    campaign_path = tmp_path / "campaigns" / "now-them-go-hear-me"
    assert result.exit_code == 0
    assert "Created campaign" in result.stdout
    assert campaign_path.is_dir()
    assert (campaign_path / "campaign.yaml").is_file()


def test_campaign_create_supports_artist_override(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "create", "No Break", "--artist", "Kelvin Rankie & Friends"],
    )

    manifest_path = tmp_path / "campaigns" / "no-break" / "campaign.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0
    assert manifest["artist"] == "Kelvin Rankie & Friends"


def test_campaign_create_rejects_duplicate(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    first = runner.invoke(app, ["campaign", "create", "Na You"])
    second = runner.invoke(app, ["campaign", "create", "Na You"])

    assert first.exit_code == 0
    assert second.exit_code == 1
    assert "Campaign already exists" in second.stdout
