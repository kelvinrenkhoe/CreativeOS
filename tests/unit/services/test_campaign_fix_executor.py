"""Tests for safe campaign fix execution."""

from pathlib import Path

import pytest

from models.campaign_fix import CampaignFix, CampaignFixPlan
from services.campaign_fix_executor import CampaignFixExecutor


def fix(
    source_check: str,
    *,
    kind: str = "automatic",
    operation: str = "create-file",
    target: str | None = None,
) -> CampaignFix:
    return CampaignFix(
        category="Campaign",
        source_check=source_check,
        title=f"Fix {source_check}",
        kind=kind,
        operation=operation,
        target=target,
        detail="Apply a safe campaign fix.",
        priority=1,
    )


def plan(*fixes: CampaignFix) -> CampaignFixPlan:
    return CampaignFixPlan(campaign_name="No Lose Guard", fixes=fixes)


def test_executor_creates_safe_directories_and_templates(tmp_path: Path) -> None:
    execution = CampaignFixExecutor().execute(
        tmp_path,
        plan(
            fix(
                "Artwork",
                operation="ensure-directory",
                target="campaigns/no-lose-guard/assets/artwork",
            ),
            fix(
                "Content calendar",
                target="campaigns/no-lose-guard/schedule/content-calendar.md",
            ),
            fix(
                "Radio outreach",
                target="campaigns/no-lose-guard/radio/stations.csv",
            ),
        ),
    )

    assert len(execution.applied) == 3
    assert (tmp_path / "campaigns/no-lose-guard/assets/artwork").is_dir()
    assert (tmp_path / "campaigns/no-lose-guard/schedule/content-calendar.md").read_text(
        encoding="utf-8"
    ) == "# Content Calendar\n"
    assert (tmp_path / "campaigns/no-lose-guard/radio/stations.csv").read_text(
        encoding="utf-8"
    ) == "station,contact,status,notes\n"


def test_executor_is_idempotent_and_never_overwrites_files(tmp_path: Path) -> None:
    target = tmp_path / "campaigns/no-lose-guard/press/press-release.md"
    target.parent.mkdir(parents=True)
    target.write_text("User content\n", encoding="utf-8")
    executor = CampaignFixExecutor()
    fix_plan = plan(
        fix(
            "Press release",
            target="campaigns/no-lose-guard/press/press-release.md",
        )
    )

    first = executor.execute(tmp_path, fix_plan)
    second = executor.execute(tmp_path, fix_plan)

    assert len(first.already_present) == 1
    assert len(second.already_present) == 1
    assert target.read_text(encoding="utf-8") == "User content\n"


def test_executor_skips_manual_unsupported_and_command_fixes(tmp_path: Path) -> None:
    execution = CampaignFixExecutor().execute(
        tmp_path,
        plan(
            fix(
                "Release date",
                kind="manual",
                operation="update-configuration",
                target="campaigns/no-lose-guard/campaign.yaml",
            ),
            fix(
                "Campaign manifest",
                kind="unsupported",
                operation="unsupported",
                target="campaigns/no-lose-guard/campaign.yaml",
            ),
            fix(
                "Campaign workspace",
                operation="run-command",
                target='creativeos campaign create "No Lose Guard"',
            ),
        ),
    )

    assert len(execution.skipped) == 3
    assert not (tmp_path / "campaigns").exists()


def test_executor_skips_unapproved_file_templates(tmp_path: Path) -> None:
    execution = CampaignFixExecutor().execute(
        tmp_path,
        plan(
            fix(
                "Custom automatic fix",
                target="campaigns/no-lose-guard/custom.md",
            )
        ),
    )

    assert len(execution.skipped) == 1
    assert not (tmp_path / "campaigns/no-lose-guard/custom.md").exists()


@pytest.mark.parametrize(
    "target",
    ["/tmp/outside", "../outside", "campaigns/../../outside"],
)
def test_executor_rejects_targets_outside_workspace(
    tmp_path: Path,
    target: str,
) -> None:
    with pytest.raises(ValueError, match="workspace"):
        CampaignFixExecutor().execute(
            tmp_path,
            plan(fix("Artwork", operation="ensure-directory", target=target)),
        )
