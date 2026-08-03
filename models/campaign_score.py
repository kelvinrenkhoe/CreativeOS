"""Campaign quality scoring models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignScoreCategory:
    """Score for one campaign quality category."""

    name: str
    score: int
    passed_checks: int
    total_checks: int
    findings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("category score must be between 0 and 100")
        if self.passed_checks < 0:
            raise ValueError("passed_checks must not be negative")
        if self.total_checks < 0:
            raise ValueError("total_checks must not be negative")
        if self.passed_checks > self.total_checks:
            raise ValueError("passed_checks must not exceed total_checks")


@dataclass(frozen=True)
class CampaignScore:
    """Complete deterministic campaign quality score."""

    campaign_name: str
    overall_score: int
    categories: tuple[CampaignScoreCategory, ...]

    def __post_init__(self) -> None:
        if not self.campaign_name.strip():
            raise ValueError("campaign_name must not be empty")
        if not 0 <= self.overall_score <= 100:
            raise ValueError("overall_score must be between 0 and 100")

    def category(self, name: str) -> CampaignScoreCategory:
        """Return a named category score."""
        try:
            return next(category for category in self.categories if category.name == name)
        except StopIteration as exc:
            raise KeyError(f"Unknown campaign score category: {name}") from exc
