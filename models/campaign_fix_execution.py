"""Campaign fix execution result models."""

from dataclasses import dataclass

VALID_EXECUTION_STATUSES = frozenset({"applied", "already-present", "skipped"})


@dataclass(frozen=True)
class CampaignFixResult:
    """Result of evaluating or applying one planned campaign fix."""

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
        if self.status not in VALID_EXECUTION_STATUSES:
            raise ValueError("status must be one of: already-present, applied, skipped")
        if not self.detail.strip():
            raise ValueError("detail must not be empty")


@dataclass(frozen=True)
class CampaignFixExecutionReport:
    """Complete outcome of safely executing one campaign fix plan."""

    campaign_name: str
    results: tuple[CampaignFixResult, ...]

    def __post_init__(self) -> None:
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")

    @property
    def applied(self) -> tuple[CampaignFixResult, ...]:
        """Return fixes that changed the workspace."""
        return tuple(result for result in self.results if result.status == "applied")

    @property
    def already_present(self) -> tuple[CampaignFixResult, ...]:
        """Return fixes whose target already existed."""
        return tuple(result for result in self.results if result.status == "already-present")

    @property
    def skipped(self) -> tuple[CampaignFixResult, ...]:
        """Return fixes intentionally not executed."""
        return tuple(result for result in self.results if result.status == "skipped")
