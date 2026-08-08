"""Read-only sequence planning for campaign content inventories."""

from models.content_item import ContentItem
from models.content_sequence_plan import (
    ContentAdjacencySignal,
    ContentSequenceEntry,
    ContentSequencePlan,
)
from services.content_inventory import ContentInventoryRepository


class ContentSequencePlanError(ValueError):
    """Raised when a proposed content sequence cannot be evaluated safely."""


class ContentSequencePlanService:
    """Evaluate an explicitly supplied content order without mutating campaign state."""

    def __init__(self, repository: ContentInventoryRepository) -> None:
        self.repository = repository

    def plan(self, content_ids: tuple[str, ...]) -> ContentSequencePlan:
        """Load content in the supplied order and return a read-only sequence plan."""
        if len(set(content_ids)) != len(content_ids):
            raise ContentSequencePlanError("content sequence ids must be unique")
        items = tuple(self.repository.load(content_id) for content_id in content_ids)
        return build_content_sequence_plan(items)


def build_content_sequence_plan(items: tuple[ContentItem, ...]) -> ContentSequencePlan:
    """Evaluate adjacent variation while preserving the supplied item order."""
    entries = tuple(
        ContentSequenceEntry(
            position=index,
            content_id=item.content_id,
            content_role=item.content_role,
            content_format=item.content_format,
            channel=item.channel,
            call_to_action=item.brief.call_to_action,
        )
        for index, item in enumerate(items, start=1)
    )

    signals = tuple(
        ContentAdjacencySignal(
            left_content_id=left.content_id,
            right_content_id=right.content_id,
            shared_dimensions=_shared_dimensions(left, right),
        )
        for left, right in zip(items, items[1:], strict=False)
    )
    return ContentSequencePlan(entries=entries, adjacency_signals=signals)


def _shared_dimensions(left: ContentItem, right: ContentItem) -> tuple[str, ...]:
    dimensions: list[str] = []
    if left.content_role is not None and left.content_role == right.content_role:
        dimensions.append("role")
    if left.content_format is not None and left.content_format == right.content_format:
        dimensions.append("format")
    if left.channel is not None and left.channel == right.channel:
        dimensions.append("channel")

    left_cta = left.brief.call_to_action.strip().casefold()
    right_cta = right.brief.call_to_action.strip().casefold()
    if left_cta and left_cta == right_cta:
        dimensions.append("call-to-action")
    return tuple(dimensions)
