"""Plan-only campaign auto-fix models."""

from dataclasses import dataclass

VALID_FIX_KINDS = frozenset({"automatic", "manual", "unsupported"})
VALID_OPERATIONS = frozenset(
    {
        "ensure-directory",
        "create-file",
        "update-configuration",
        "run-command",
        "manual-action",
        "unsupported",
    }
)


@dataclass(frozen=True)
class CampaignFix:
    """One proposed campaign fix that has not been applied."""

    category: str
    source_check: str
    title: str
    kind: str
    operation: str
    target: str | None
    detail: str
    priority: int

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise ValueError("category must not be empty")
        if not self.source_check.strip():
            raise ValueError("source_check must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if self.kind not in VALID_FIX_KINDS:
            raise ValueError("kind must be one of: automatic, manual, unsupported")
        if self.operation not in VALID_OPERATIONS:
            raise ValueError("unsupported fix operation")
        if not self.detail.strip():
            raise ValueError("detail must not be empty")
        if self.priority not in {1, 2, 3}:
            raise ValueError("priority must be between 1 and 3")


@dataclass(frozen=True)
class CampaignFixPlan:
    """Complete ordered, non-mutating fix plan for one campaign."""

    campaign_name: str
    fixes: tuple[CampaignFix, ...]

    def __post_init__(self) -> None:
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")

    @property
    def automatic(self) -> tuple[CampaignFix, ...]:
        """Return fixes safe for deterministic automation."""
        return tuple(fix for fix in self.fixes if fix.kind == "automatic")

    @property
    def manual(self) -> tuple[CampaignFix, ...]:
        """Return fixes requiring user input or judgement."""
        return tuple(fix for fix in self.fixes if fix.kind == "manual")

    @property
    def unsupported(self) -> tuple[CampaignFix, ...]:
        """Return fixes without a supported safe implementation."""
        return tuple(fix for fix in self.fixes if fix.kind == "unsupported")
