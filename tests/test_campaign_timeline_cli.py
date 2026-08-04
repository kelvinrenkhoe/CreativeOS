"""CLI tests for deterministic campaign release timelines."""

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
repository:
  songs: songs
  campaigns: campaigns
  assets: assets
  knowledge: knowledge
"""


def create_workspace(root: Path) -> Path:
    """Create the minimum CreativeOS workspace required by CLI tests."""
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    campaign = root / "campaigns" / "no-lose-guard"
    campaign.mkdir(parents=True)
    return campaign


def write_manifest(campaign: Path, release_date: str | None) -> None:
    """Write one campaign manifest with an optional release date."""
    release_line = f"release_date: {release_date}\n" if release_date is not None else ""
    campaign.joinpath("campaign.yaml").write_text(
        "name: No Lose Guard\n"
        "artist: Kelvin Rankie\n"
        f"{release_line}"
        "platforms: [spotify, instagram]\n"
        "goals: [awareness]\n",
        encoding="utf-8",
    )


def test_timeline_renders_chronological_release_schedule(
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign, "2026-09-01")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "timeline", "No Lose Guard"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "CreativeOS Campaign Timeline" in output
    assert "No Lose Guard" in output
    assert "2026-09-01" in output
    assert "Release day" in output
    assert "+7" in output
    assert output.index("Pre-save campaign begins") < output.index("Release day")
    assert output.index("Release day") < output.index("Playlist push")


def test_timeline_reports_missing_release_date(tmp_path: Path, monkeypatch) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign, None)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "timeline", "No Lose Guard"])

    assert result.exit_code == 1
    output = " ".join(result.stdout.split())
    assert "Release date is not configured" in output
    assert "campaign.yaml" in output
    assert "YYYY-MM-DD" in output


def test_timeline_reports_invalid_release_date(tmp_path: Path, monkeypatch) -> None:
    campaign = create_workspace(tmp_path)
    write_manifest(campaign, "September-1-2026")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "timeline", "No Lose Guard"])

    assert result.exit_code == 1
    assert "Invalid release date" in result.stdout
    assert "YYYY-MM-DD" in result.stdout


def test_timeline_reports_unknown_campaign(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["campaign", "timeline", "Missing Campaign"])

    assert result.exit_code == 1
    output = " ".join(result.stdout.split())
    assert "Campaign workspace not found" in output
    assert 'creativeos campaign create "Missing Campaign"' in output
