"""Safe, idempotent execution of automatic campaign fixes."""

from pathlib import Path

from models.campaign_fix import CampaignFix, CampaignFixPlan
from models.campaign_fix_execution import (
    CampaignFixExecutionReport,
    CampaignFixResult,
)

FILE_TEMPLATES = {
    "Content calendar": "# Content Calendar\n",
    "Press release": "# Press Release\n",
    "Radio outreach": "station,contact,status,notes\n",
}


class CampaignFixExecutor:
    """Apply only deterministic and non-destructive campaign fixes."""

    def execute(
        self,
        root: Path,
        plan: CampaignFixPlan,
    ) -> CampaignFixExecutionReport:
        """Execute safe automatic fixes and report all skipped work."""
        workspace_root = root.resolve()
        results = tuple(self._execute_fix(workspace_root, fix) for fix in plan.fixes)
        return CampaignFixExecutionReport(
            campaign_name=plan.campaign_name,
            results=results,
        )

    def _execute_fix(
        self,
        root: Path,
        fix: CampaignFix,
    ) -> CampaignFixResult:
        if fix.kind != "automatic":
            return self._skipped(fix, f"{fix.kind} fixes are not executed automatically")

        if fix.operation == "ensure-directory":
            return self._ensure_directory(root, fix)

        if fix.operation == "create-file":
            return self._create_file(root, fix)

        return self._skipped(
            fix,
            f"operation is not permitted by the safe executor: {fix.operation}",
        )

    def _ensure_directory(
        self,
        root: Path,
        fix: CampaignFix,
    ) -> CampaignFixResult:
        target = self._safe_target(root, fix)
        if target.exists():
            if not target.is_dir():
                return self._skipped(fix, "target exists and is not a directory")
            return self._result(fix, "already-present", "directory already exists")

        target.mkdir(parents=True, exist_ok=False)
        return self._result(fix, "applied", "directory created")

    def _create_file(
        self,
        root: Path,
        fix: CampaignFix,
    ) -> CampaignFixResult:
        target = self._safe_target(root, fix)
        if target.exists():
            if not target.is_file():
                return self._skipped(fix, "target exists and is not a file")
            return self._result(fix, "already-present", "file already exists")

        content = FILE_TEMPLATES.get(fix.source_check)
        if content is None:
            return self._skipped(fix, "no approved template exists for this fix")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return self._result(fix, "applied", "template file created")

    @staticmethod
    def _safe_target(root: Path, fix: CampaignFix) -> Path:
        if fix.target is None:
            raise ValueError(f"fix target is required for {fix.source_check}")

        raw_target = Path(fix.target)
        if raw_target.is_absolute():
            raise ValueError("fix target must be relative to the workspace")

        target = (root / raw_target).resolve()
        if target != root and root not in target.parents:
            raise ValueError("fix target escapes the workspace")
        return target

    @staticmethod
    def _result(
        fix: CampaignFix,
        status: str,
        detail: str,
    ) -> CampaignFixResult:
        return CampaignFixResult(
            source_check=fix.source_check,
            operation=fix.operation,
            target=fix.target,
            status=status,
            detail=detail,
        )

    @classmethod
    def _skipped(cls, fix: CampaignFix, detail: str) -> CampaignFixResult:
        return cls._result(fix, "skipped", detail)
