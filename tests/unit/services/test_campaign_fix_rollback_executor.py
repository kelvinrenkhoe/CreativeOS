"""Tests for safe campaign fix rollback execution."""

from pathlib import Path

from models.campaign_fix_rollback import CampaignFixRollback, CampaignFixRollbackPlan
from services.campaign_fix_rollback_executor import CampaignFixRollbackExecutor


def action(
    operation: str,
    target: str | None,
    *,
    safe: bool = True,
) -> CampaignFixRollback:
    return CampaignFixRollback(
        source_check="Rollback check",
        operation=operation,
        target=target,
        detail="Rollback action.",
        safe=safe,
    )


def plan(*actions: CampaignFixRollback) -> CampaignFixRollbackPlan:
    return CampaignFixRollbackPlan(
        campaign_name="No Lose Guard",
        actions=actions,
    )


def test_executor_removes_file_and_empty_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "campaigns/no-lose-guard/schedule/content-calendar.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("# Calendar\n", encoding="utf-8")
    directory = tmp_path / "campaigns/no-lose-guard/assets/artwork"
    directory.mkdir(parents=True)

    report = CampaignFixRollbackExecutor().execute(
        tmp_path,
        plan(
            action(
                "remove-file",
                "campaigns/no-lose-guard/schedule/content-calendar.md",
            ),
            action(
                "remove-directory",
                "campaigns/no-lose-guard/assets/artwork",
            ),
        ),
    )

    assert [result.status for result in report.results] == ["removed", "removed"]
    assert not file_path.exists()
    assert not directory.exists()


def test_executor_dry_run_does_not_change_workspace(tmp_path: Path) -> None:
    file_path = tmp_path / "campaigns/no-lose-guard/press/press-release.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("# Press Release\n", encoding="utf-8")

    report = CampaignFixRollbackExecutor().execute(
        tmp_path,
        plan(
            action(
                "remove-file",
                "campaigns/no-lose-guard/press/press-release.md",
            ),
        ),
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.results[0].status == "would-remove"
    assert file_path.exists()


def test_executor_preserves_non_empty_directory(tmp_path: Path) -> None:
    directory = tmp_path / "campaigns/no-lose-guard/assets/artwork"
    directory.mkdir(parents=True)
    (directory / "cover.png").write_bytes(b"art")

    report = CampaignFixRollbackExecutor().execute(
        tmp_path,
        plan(
            action(
                "remove-directory",
                "campaigns/no-lose-guard/assets/artwork",
            ),
        ),
    )

    assert report.results[0].status == "skipped"
    assert "not empty" in report.results[0].detail
    assert directory.exists()


def test_executor_skips_target_outside_workspace(tmp_path: Path) -> None:
    report = CampaignFixRollbackExecutor().execute(
        tmp_path,
        plan(action("remove-file", "../outside.txt")),
    )

    assert report.results[0].status == "skipped"
    assert "outside the workspace" in report.results[0].detail


def test_executor_reports_missing_target(tmp_path: Path) -> None:
    report = CampaignFixRollbackExecutor().execute(
        tmp_path,
        plan(action("remove-file", "campaigns/no-lose-guard/missing.md")),
    )

    assert report.results[0].status == "missing"


def test_executor_skips_unsafe_action(tmp_path: Path) -> None:
    report = CampaignFixRollbackExecutor().execute(
        tmp_path,
        plan(action("skip", None, safe=False)),
    )

    assert report.results[0].status == "skipped"
