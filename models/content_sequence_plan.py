"""Read-only models for evaluating proposed campaign content order."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentSequenceEntry:
    """One content item positioned in a proposed sequence."""

    position: int
    content_id: str
    content_role: str | None
    content_format: str | None
    channel: str | None
    call_to_action: str


@dataclass(frozen=True, slots=True)
class ContentAdjacencySignal:
    """Variation signal for two adjacent content items."""

    left_content_id: str
    right_content_id: str
    shared_dimensions: tuple[str, ...]

    @property
    def weak_variation(self) -> bool:
        """Return whether adjacent items repeat at least three meaningful dimensions."""
        return len(self.shared_dimensions) >= 3


@dataclass(frozen=True, slots=True)
class ContentSequencePlan:
    """Read-only view of a proposed content order and its adjacency signals."""

    entries: tuple[ContentSequenceEntry, ...]
    adjacency_signals: tuple[ContentAdjacencySignal, ...]

    @property
    def weak_adjacencies(self) -> tuple[ContentAdjacencySignal, ...]:
        """Return adjacent pairs with weak variation."""
        return tuple(signal for signal in self.adjacency_signals if signal.weak_variation)

    @property
    def has_weak_variation(self) -> bool:
        """Return whether the proposed sequence contains weak adjacent variation."""
        return bool(self.weak_adjacencies)
