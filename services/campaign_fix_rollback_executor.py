"""Safely execute deterministic campaign fix rollback plans."""

from pathlib import Path

from models.campaign_fix_rollback import CampaignFixRollback, CampaignFixRollbackPlan
from models.campaign_fix_rollback_execution import (
    CampaignFixRollbackExecutionReport,
    CampaignFixRollbackResult,
)


class CampaignFixRollbackExecutor:
    """Execute only safe rollback actions within a workspace root."""

    def execute(
        self,
        workspace_root: Path,
        plan: CampaignFixRollbackPlan,
        *,
        dry_run: bool = False,
    ) -> CampaignFixRollbackExecutionReport:
        """Execute a rollback plan and return a complete report."""
        root = workspace_root.resolve()
        results = tuple(
            self._execute_action(root, action, dry_run=dry_run) for action in plan.actions
        )
        return CampaignFixRollbackExecutionReport(
            campaign_name=plan.campaign_name,
            dry_run=dry_run,
            results=results,
        )

    def _execute_action(
        self,
        root: Path,
        action: CampaignFixRollback,
        *,
        dry_run: bool,
    ) -> CampaignFixRollbackResult:
        if not action.safe or action.operation == "skip":
            return self._result(
                action,
                status="skipped",
                detail=action.detail,
            )

        if not action.target:
            return self._result(
                action,
                status="skipped",
                detail="Rollback target is missing.",
            )

        target = self._resolve_target(root, action.target)
        if target is None:
            return self._result(
                action,
                status="skipped",
                detail="Rollback target is outside the workspace.",
            )

        if action.operation == "remove-file":
            return self._remove_file(action, target, dry_run=dry_run)
        if action.operation == "remove-directory":
            return self._remove_directory(action, target, dry_run=dry_run)

        return self._result(
            action,
            status="skipped",
            detail=f"Unsupported rollback operation: {action.operation}",
        )

    @staticmethod
    def _resolve_target(root: Path, target: str) -> Path | None:
        candidate = (root / target).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate

    def _remove_file(
        self,
        action: CampaignFixRollback,
        target: Path,
        *,
        dry_run: bool,
    ) -> CampaignFixRollbackResult:
        if not target.exists():
            return self._result(
                action,
                status="missing",
                detail="File is already absent.",
            )
        if not target.is_file():
            return self._result(
                action,
                status="skipped",
                detail="Rollback target is not a file.",
            )
        if dry_run:
            return self._result(
                action,
                status="would-remove",
                detail="Dry run: file would be removed.",
            )

        target.unlink()
        return self._result(
            action,
            status="removed",
            detail="Removed file.",
        )

    def _remove_directory(
        self,
        action: CampaignFixRollback,
        target: Path,
        *,
        dry_run: bool,
    ) -> CampaignFixRollbackResult:
        if not target.exists():
            return self._result(
                action,
                status="missing",
                detail="Directory is already absent.",
            )
        if not target.is_dir():
            return self._result(
                action,
                status="skipped",
                detail="Rollback target is not a directory.",
            )
        if any(target.iterdir()):
            return self._result(
                action,
                status="skipped",
                detail="Directory is not empty and was preserved.",
            )
        if dry_run:
            return self._result(
                action,
                status="would-remove",
                detail="Dry run: empty directory would be removed.",
            )

        target.rmdir()
        return self._result(
            action,
            status="removed",
            detail="Removed empty directory.",
        )

    @staticmethod
    def _result(
        action: CampaignFixRollback,
        *,
        status: str,
        detail: str,
    ) -> CampaignFixRollbackResult:
        return CampaignFixRollbackResult(
            source_check=action.source_check,
            operation=action.operation,
            target=action.target,
            status=status,
            detail=detail,
        )
