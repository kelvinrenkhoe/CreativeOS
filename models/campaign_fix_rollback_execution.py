"""Campaign fix rollback execution result models."""

from dataclasses import dataclass

VALID_ROLLBACK_EXECUTION_STATUSES = frozenset(
    {"removed", "would-remove", "missing", "skipped"}
)


@dataclass(frozen=True)
class CampaignFixRollbackResult:
    """Outcome of evaluating or executing one rollback action."""

    source_check: str
    operation: str
    target: str | None
    status: str
    detail: str

    def __post_init__(self) -> None:
        if not self.source_check.strip():
            raise ValueError("source_check must not be empty")
        if not self.operation.strip():
            raise ValueError("operation must not be empty")
        if self.status not in VALID_ROLLBACK_EXECUTION_STATUSES:
            raise ValueError(
                "status must be one of: missing, removed, skipped, would-remove"
            )
        if not self.detail.strip():
            raise ValueError("detail must not be empty")


@dataclass(frozen=True)
class CampaignFixRollbackExecutionReport:
    """Complete outcome of executing one campaign rollback plan."""

    campaign_name: str
    dry_run: bool
    results: tuple[CampaignFixRollbackResult, ...]

    def __post_init__(self) -> None:
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")

    @property
    def removed(self) -> tuple[CampaignFixRollbackResult, ...]:
        """Return targets removed from the workspace."""
        return tuple(result for result in self.results if result.status == "removed")

    @property
    def would_remove(self) -> tuple[CampaignFixRollbackResult, ...]:
        """Return targets a dry run would remove."""
        return tuple(
            result for result in self.results if result.status == "would-remove"
        )

    @property
    def missing(self) -> tuple[CampaignFixRollbackResult, ...]:
        """Return targets already absent from the workspace."""
        return tuple(result for result in self.results if result.status == "missing")

    @property
    def skipped(self) -> tuple[CampaignFixRollbackResult, ...]:
        """Return rollback actions intentionally not executed."""
        return tuple(result for result in self.results if result.status == "skipped")
