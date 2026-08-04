"""CLI tests for read-only campaign fix rollback planning."""

from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from cli.main import app
from models.campaign_fix_execution import CampaignFixExecutionReport, CampaignFixResult
from services.campaign_fix_receipts import JsonCampaignFixReceiptStore

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


def create_workspace(root: Path) -> None:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir(parents=True, exist_ok=True)


def save_receipt(root: Path) -> None:
    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            CampaignFixResult(
                source_check="Artwork",
                operation="ensure-directory",
                target="campaigns/no-lose-guard/assets/artwork",
                status="applied",
                detail="Created directory.",
            ),
            CampaignFixResult(
                source_check="Content calendar",
                operation="create-file",
                target="campaigns/no-lose-guard/schedule/content-calendar.md",
                status="applied",
                detail="Created template.",
            ),
            CampaignFixResult(
                source_check="Press release",
                operation="create-file",
                target="campaigns/no-lose-guard/press/press-release.md",
                status="already-present",
                detail="Preserved existing file.",
            ),
        ),
    )
    JsonCampaignFixReceiptStore(root / ".creativeos" / "campaign-fix-receipts").save(report)


def test_rollback_plan_renders_latest_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_workspace(tmp_path)
    save_receipt(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "cli.campaign_fix_rollback.console",
        Console(width=200),
    )

    result = runner.invoke(
        app,
        ["campaign", "rollback-plan", "No Lose Guard"],
    )

    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "CreativeOS Campaign Rollback Plan" in output
    assert "No Lose Guard" in output
    assert "remove-file" in output
    assert "remove-directory" in output
    assert "content-calendar.md" in output
    assert "Nothing has been changed" in output
    assert "press-release.md" not in output


def test_rollback_plan_requires_fix_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "rollback-plan", "No Lose Guard"],
    )

    assert result.exit_code == 1
    output = " ".join(result.stdout.split())
    assert "No campaign fix receipt found" in output
    assert "creativeos campaign fix" in output


def test_rollback_plan_requires_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "rollback-plan", "No Lose Guard"],
    )

    assert result.exit_code == 1
    assert "CreativeOS workspace not found" in result.stdout
