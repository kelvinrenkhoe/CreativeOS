"""Tests for campaign fix rollback planning."""

from models.campaign_fix_execution import CampaignFixExecutionReport, CampaignFixResult
from services.campaign_fix_rollback import CampaignFixRollbackPlanner


def result(
    source_check: str,
    *,
    operation: str,
    target: str | None,
    status: str = "applied",
) -> CampaignFixResult:
    return CampaignFixResult(
        source_check=source_check,
        operation=operation,
        target=target,
        status=status,
        detail="Execution result.",
    )


def test_planner_reverses_only_applied_results() -> None:
    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            result(
                "Artwork",
                operation="ensure-directory",
                target="campaigns/no-lose-guard/assets/artwork",
            ),
            result(
                "Content calendar",
                operation="create-file",
                target="campaigns/no-lose-guard/schedule/content-calendar.md",
            ),
            result(
                "Press release",
                operation="create-file",
                target="campaigns/no-lose-guard/press/press-release.md",
                status="already-present",
            ),
            result(
                "Release date",
                operation="update-configuration",
                target="campaigns/no-lose-guard/campaign.yaml",
                status="skipped",
            ),
        ),
    )

    plan = CampaignFixRollbackPlanner().plan(report)

    assert [action.source_check for action in plan.actions] == [
        "Content calendar",
        "Artwork",
    ]
    assert [action.operation for action in plan.actions] == [
        "remove-file",
        "remove-directory",
    ]


def test_planner_marks_unknown_applied_operation_as_unsafe() -> None:
    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            result(
                "Custom",
                operation="manual-action",
                target="campaigns/no-lose-guard/custom",
            ),
        ),
    )

    plan = CampaignFixRollbackPlanner().plan(report)

    assert len(plan.safe_actions) == 0
    assert len(plan.skipped_actions) == 1
    assert plan.skipped_actions[0].operation == "skip"


def test_planner_is_deterministic() -> None:
    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(
            result(
                "Radio outreach",
                operation="create-file",
                target="campaigns/no-lose-guard/radio/stations.csv",
            ),
        ),
    )
    planner = CampaignFixRollbackPlanner()

    assert planner.plan(report) == planner.plan(report)


def test_empty_execution_report_returns_empty_plan() -> None:
    report = CampaignFixExecutionReport(
        campaign_name="No Lose Guard",
        results=(),
    )

    plan = CampaignFixRollbackPlanner().plan(report)

    assert plan.actions == ()
