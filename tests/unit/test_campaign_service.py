from pathlib import Path

import pytest
import yaml

from core.project import Project
from services.campaign import CampaignService, slugify

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


def create_workspace(root: Path) -> Project:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    return Project(root)


def test_slugify_campaign_name() -> None:
    assert slugify("Now Them Go Hear Me") == "now-them-go-hear-me"
    assert slugify("  Na You!  ") == "na-you"


def test_slugify_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        slugify("---")


def test_create_campaign_workspace(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    campaign_path = CampaignService(project).create("Now Them Go Hear Me")

    assert campaign_path == tmp_path / "campaigns" / "now-them-go-hear-me"
    assert (campaign_path / "campaign.yaml").is_file()
    assert (campaign_path / "README.md").is_file()
    assert (campaign_path / "captions" / "instagram.md").is_file()
    assert (campaign_path / "radio" / "stations.csv").is_file()
    assert (campaign_path / "schedule" / "content-calendar.md").is_file()
    assert (campaign_path / "assets" / "artwork").is_dir()
    assert (campaign_path / "assets" / "videos").is_dir()
    assert (campaign_path / "assets" / "photos").is_dir()


def test_manifest_uses_project_artist(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    campaign_path = CampaignService(project).create("Carry Your Name")
    manifest = yaml.safe_load((campaign_path / "campaign.yaml").read_text(encoding="utf-8"))

    assert manifest["name"] == "Carry Your Name"
    assert manifest["artist"] == "Kelvin Rankie"
    assert manifest["status"] == "planning"
    assert "spotify" in manifest["platforms"]
    assert manifest["goals"]["radio_stations"] == 100


def test_artist_can_be_overridden(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)

    campaign_path = CampaignService(project).create("No Break", artist="Guest Artist")
    manifest = yaml.safe_load((campaign_path / "campaign.yaml").read_text(encoding="utf-8"))

    assert manifest["artist"] == "Guest Artist"


def test_existing_campaign_is_not_overwritten(tmp_path: Path) -> None:
    project = create_workspace(tmp_path)
    service = CampaignService(project)
    service.create("Na You")

    with pytest.raises(FileExistsError):
        service.create("Na You")
