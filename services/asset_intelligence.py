"""Deterministic novelty and repetition signals for campaign assets."""

import re
from dataclasses import dataclass

from services.campaign_memory import CampaignMemory, CampaignMemoryEntry


_WORD = re.compile(r"[\w']+")


@dataclass(frozen=True, slots=True)
class NoveltyAssessment:
    """Similarity-based assessment of one proposed campaign asset."""

    novelty_score: float
    similarity_score: float
    is_repetitive: bool
    closest_entry: CampaignMemoryEntry | None

    @property
    def recommendation(self) -> str:
        """Return a concise action for downstream planners and reviewers."""
        if self.closest_entry is None:
            return "use"
        if self.is_repetitive:
            return "revise"
        return "use"


class AssetIntelligenceService:
    """Compare proposed assets with campaign memory without provider coupling."""

    def __init__(self, *, repetition_threshold: float = 0.7, shingle_size: int = 2) -> None:
        if not 0 <= repetition_threshold <= 1:
            raise ValueError("repetition_threshold must be between 0 and 1")
        if shingle_size < 1:
            raise ValueError("shingle_size must be at least 1")
        self.repetition_threshold = repetition_threshold
        self.shingle_size = shingle_size

    def assess(self, content: str, memory: CampaignMemory) -> NoveltyAssessment:
        """Assess content novelty against all recorded campaign assets."""
        if not content.strip():
            raise ValueError("content must not be empty")

        proposed = self._shingles(content)
        closest_entry: CampaignMemoryEntry | None = None
        highest_similarity = 0.0

        for entry in memory.entries:
            similarity = self._similarity(proposed, self._shingles(entry.content))
            if closest_entry is None or similarity > highest_similarity:
                closest_entry = entry
                highest_similarity = similarity

        return NoveltyAssessment(
            novelty_score=round(1 - highest_similarity, 4),
            similarity_score=round(highest_similarity, 4),
            is_repetitive=bool(closest_entry) and highest_similarity >= self.repetition_threshold,
            closest_entry=closest_entry,
        )

    def _shingles(self, content: str) -> frozenset[tuple[str, ...]]:
        words = [word.casefold() for word in _WORD.findall(content)]
        if len(words) < self.shingle_size:
            return frozenset((word,) for word in words)
        return frozenset(
            tuple(words[index : index + self.shingle_size])
            for index in range(len(words) - self.shingle_size + 1)
        )

    @staticmethod
    def _similarity(
        left: frozenset[tuple[str, ...]],
        right: frozenset[tuple[str, ...]],
    ) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)
