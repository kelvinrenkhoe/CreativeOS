"""Structured campaign recommendation models."""

from dataclasses import dataclass

VALID_IMPACTS = frozenset({"low", "medium", "high"})
VALID_PRIORITIES = frozenset({1, 2, 3})


@dataclass(frozen=True)
class CampaignRecommendation:
    """One deterministic recommendation for improving a campaign."""

    category: str
    source_check: str
    title: str
    detail: str
    action: str | None
    impact: str
    priority: int

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise ValueError("category must not be empty")
        if not self.source_check.strip():
            raise ValueError("source_check must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.detail.strip():
            raise ValueError("detail must not be empty")
        if self.impact not in VALID_IMPACTS:
            raise ValueError("impact must be one of: high, low, medium")
        if self.priority not in VALID_PRIORITIES:
            raise ValueError("priority must be between 1 and 3")


@dataclass(frozen=True)
class CampaignRecommendations:
    """Complete ordered recommendations for one campaign."""

    campaign_name: str
    items: tuple[CampaignRecommendation, ...]

    def __post_init__(self) -> None:
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")

    @property
    def high_impact_count(self) -> int:
        """Return the number of high-impact recommendations."""
        return sum(item.impact == "high" for item in self.items)

    @property
    def actionable_count(self) -> int:
        """Return recommendations containing an action."""
        return sum(item.action is not None for item in self.items)
