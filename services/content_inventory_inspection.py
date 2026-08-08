"""Read-only inspection for campaign content coverage and variation."""

from collections import Counter, defaultdict

from models.content_inventory_report import ContentInventoryReport, ContentVariationGroup
from models.content_item import ContentItem
from services.content_inventory import ContentInventoryRepository


class ContentInventoryInspectionService:
    """Summarize one campaign content inventory without mutating it."""

    def __init__(self, repository: ContentInventoryRepository) -> None:
        self.repository = repository

    def inspect(self) -> ContentInventoryReport:
        """Return deterministic coverage and repetition signals for the campaign."""
        items = self.repository.list()
        return inspect_content_items(items)


def inspect_content_items(items: tuple[ContentItem, ...]) -> ContentInventoryReport:
    """Inspect already-loaded content items for coverage and repeated signatures."""
    role_counts = Counter(item.content_role for item in items if item.content_role is not None)
    format_counts = Counter(
        item.content_format for item in items if item.content_format is not None
    )
    channel_counts = Counter(item.channel for item in items if item.channel is not None)

    repeated: dict[tuple[str | None, str | None, str | None, str], list[str]] = defaultdict(list)
    for item in items:
        signature = (
            item.content_role,
            item.content_format,
            item.channel,
            item.brief.call_to_action.casefold(),
        )
        repeated[signature].append(item.content_id)

    sorted_groups = sorted(
        repeated.items(),
        key=lambda entry: tuple(value or "" for value in entry[0]),
    )
    repeated_groups = tuple(
        ContentVariationGroup(
            content_ids=tuple(content_ids),
            content_role=signature[0],
            content_format=signature[1],
            channel=signature[2],
            call_to_action=signature[3],
        )
        for signature, content_ids in sorted_groups
        if len(content_ids) > 1
    )

    return ContentInventoryReport(
        total_items=len(items),
        roles=tuple(sorted(role_counts.items())),
        formats=tuple(sorted(format_counts.items())),
        channels=tuple(sorted(channel_counts.items())),
        missing_role_ids=tuple(item.content_id for item in items if item.content_role is None),
        missing_format_ids=tuple(item.content_id for item in items if item.content_format is None),
        missing_channel_ids=tuple(item.content_id for item in items if item.channel is None),
        missing_call_to_action_ids=tuple(
            item.content_id for item in items if not item.brief.call_to_action
        ),
        repeated_groups=repeated_groups,
    )
