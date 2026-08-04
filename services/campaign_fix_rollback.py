"""Build safe rollback plans from campaign fix execution reports."""

from models.campaign_fix_execution import CampaignFixExecutionReport, CampaignFixResult
from models.campaign_fix_rollback import CampaignFixRollback, CampaignFixRollbackPlan


class CampaignFixRollbackPlanner:
    """Convert applied fix results into deterministic rollback actions."""

    def plan(self, report: CampaignFixExecutionReport) -> CampaignFixRollbackPlan:
        """Return rollback actions without changing the workspace."""
        actions = tuple(
            action
            for result in reversed(report.results)
            for action in (self._action_for(result),)
            if action is not None
        )
        return CampaignFixRollbackPlan(
            campaign_name=report.campaign_name,
            actions=actions,
        )

    @staticmethod
    def _action_for(result: CampaignFixResult) -> CampaignFixRollback | None:
        if result.status != "applied":
            return None

        if result.operation == "create-file":
            return CampaignFixRollback(
                source_check=result.source_check,
                operation="remove-file",
                target=result.target,
                detail="Remove the file created by Campaign Fix.",
                safe=True,
            )

        if result.operation == "ensure-directory":
            return CampaignFixRollback(
                source_check=result.source_check,
                operation="remove-directory",
                target=result.target,
                detail="Remove the directory only if it remains empty.",
                safe=True,
            )

        return CampaignFixRollback(
            source_check=result.source_check,
            operation="skip",
            target=result.target,
            detail=f"No safe rollback mapping for operation: {result.operation}",
            safe=False,
        )
