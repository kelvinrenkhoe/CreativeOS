"""Plan-only models for rolling back applied campaign fixes."""

from dataclasses import dataclass

VALID_ROLLBACK_OPERATIONS = frozenset({"remove-file", "remove-directory", "skip"})


@dataclass(frozen=True)
class CampaignFixRollback:
    """One proposed rollback action for an applied campaign fix."""

    source_check: str
    operation: str
    target: str | None
    detail: str
    safe: bool

    def __post_init__(self) -> None:
        if not self.source_check.strip():
            raise ValueError("source_check must not be empty")
        if self.operation not in VALID_ROLLBACK_OPERATIONS:
            raise ValueError("unsupported rollback operation")
        if not self.detail.strip():
            raise ValueError("detail must not be empty")
        if self.safe and self.operation == "skip":
            raise ValueError("safe rollback actions must be executable")
        if self.operation != "skip" and not self.target:
            raise ValueError("rollback target is required")


@dataclass(frozen=True)
class CampaignFixRollbackPlan:
    """Complete non-mutating rollback plan for one fix execution."""

    campaign_name: str
    actions: tuple[CampaignFixRollback, ...]

    def __post_init__(self) -> None:
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")

    @property
    def safe_actions(self) -> tuple[CampaignFixRollback, ...]:
        """Return rollback actions safe for deterministic execution."""
        return tuple(action for action in self.actions if action.safe)

    @property
    def skipped_actions(self) -> tuple[CampaignFixRollback, ...]:
        """Return rollback actions intentionally left for review."""
        return tuple(action for action in self.actions if not action.safe)
