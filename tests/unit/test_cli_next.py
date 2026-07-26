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

UNIVERSE = """
id: kelvin-rankie-universe
name: Kelvin Rankie Universe
works:
  - id: no-way-back
    name: No Way Back
    kind: song
arcs:
  - id: journey
    name: Journey
    beats:
      - id: pressure
        summary: Establish the pressure to leave.
      - id: resolve
        summary: Reveal resilience and hope.
relationships:
  - source_id: no-way-back
    target_id: journey
    kind: follows
"""


def create_workspace(root: Path) -> None:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    (root / "universe.yaml").write_text(UNIVERSE, encoding="utf-8")


def test_next_command_renders_the_active_recommendation(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "next",
            "no-way-back",
            "--week",
            "3",
            "--weeks",
            "4",
            "--objective",
            "Grow meaningful streams",
            "--audience",
            "Afrobeats listeners",
            "--tone",
            "Cinematic and hopeful",
            "--platform",
            "Instagram",
            "--platform",
            "TikTok",
        ],
    )

    assert result.exit_code == 0
    assert "Next Recommendation: No Way Back" in result.stdout
    assert "Campaign week: 3 of 4" in result.stdout
    assert "Active phase: 2 — Resolve" in result.stdout
    assert "Platforms: instagram, tiktok" in result.stdout


def test_next_command_reports_an_invalid_week(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "next",
            "no-way-back",
            "--week",
            "5",
            "--weeks",
            "4",
            "--objective",
            "Grow streams",
            "--audience",
            "Afrobeats listeners",
            "--tone",
            "Hopeful",
            "--platform",
            "Instagram",
        ],
    )

    assert result.exit_code == 1
    assert "week must be between 1 and 4" in result.stdout
