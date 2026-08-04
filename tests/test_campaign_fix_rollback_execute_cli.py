"""CLI tests for campaign fix rollback execution."""

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


def prepare_fix_receipt(root: Path) -> tuple[Path, Path]:
    created_file = root / "campaigns/no-lose-guard/schedule/content-calendar.md"
    created_directory = root / "campaigns/no-lose-guard/assets/artwork"
    created_file.parent.mkdir(parents=True, exist_ok=True)
    created_file.write_text("# Content Calendar\n", encoding="utf-8")
    created_directory.mkdir(parents=True, exist_ok=True)

    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            CampaignFixResult(
                source_check="Content calendar",
                operation="create-file",
                target="campaigns/no-lose-guard/schedule/content-calendar.md",
                status="applied",
                detail="Created template.",
            ),
            CampaignFixResult(
                source_check="Artwork",
                operation="ensure-directory",
                target="campaigns/no-lose-guard/assets/artwork",
                status="applied",
                detail="Created directory.",
            ),
        ),
    )
    JsonCampaignFixReceiptStore(
        root / ".creativeos" / "campaign-fix-receipts"
    ).save(report)
    return created_file, created_directory


def widen_console(monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.campaign_fix_rollback_execute.console",
        Console(width=180),
    )


def test_rollback_dry_run_preserves_targets(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    created_file, created_directory = prepare_fix_receipt(tmp_path)
    monkeypatch.chdir(tmp_path)
    widen_console(monkeypatch)

    result = runner.invoke(
        app,
        ["campaign", "rollback", "No Lose Guard", "--dry-run"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "CreativeOS Campaign Rollback" in output
    assert "Dry run" in output
    assert "would-remove" in output
    assert "nothing was changed" in output
    assert created_file.is_file()
    assert created_directory.is_dir()


def test_rollback_yes_removes_safe_targets(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    created_file, created_directory = prepare_fix_receipt(tmp_path)
    monkeypatch.chdir(tmp_path)
    widen_console(monkeypatch)

    result = runner.invoke(
        app,
        ["campaign", "rollback", "No Lose Guard", "--yes"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    output = " ".join(result.stdout.split())
    assert "Rollback execution completed" in output
    assert "removed" in output
    assert not created_file.exists()
    assert not created_directory.exists()


def test_rollback_can_be_cancelled(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    created_file, created_directory = prepare_fix_receipt(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "rollback", "No Lose Guard"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Rollback cancelled" in result.stdout
    assert created_file.exists()
    assert created_directory.exists()


def test_rollback_requires_receipt(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["campaign", "rollback", "No Lose Guard", "--yes"],
    )

    assert result.exit_code == 1
    assert "No campaign fix receipt found" in result.stdout
