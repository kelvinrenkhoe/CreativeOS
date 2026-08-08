"""Deterministic recommendation models for campaign content sequencing."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentSequenceRecommendation:
    """One read-only recommendation for improving campaign content variation."""

    recommendation_id: str
    summary: str
    content_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContentSequenceRecommendationReport:
    """Campaign-level sequencing recommendations derived from inventory inspection."""

    recommendations: tuple[ContentSequenceRecommendation, ...]

    @property
    def has_recommendations(self) -> bool:
        """Return whether the campaign has any sequencing recommendations."""
        return bool(self.recommendations)
