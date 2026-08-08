"""Read-only campaign content inventory inspection models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentVariationGroup:
    """One repeated content signature detected in a campaign inventory."""

    content_ids: tuple[str, ...]
    content_role: str | None
    content_format: str | None
    channel: str | None
    call_to_action: str


@dataclass(frozen=True, slots=True)
class ContentInventoryReport:
    """Campaign-level view of content coverage and variation."""

    total_items: int
    roles: tuple[tuple[str, int], ...]
    formats: tuple[tuple[str, int], ...]
    channels: tuple[tuple[str, int], ...]
    missing_role_ids: tuple[str, ...]
    missing_format_ids: tuple[str, ...]
    missing_channel_ids: tuple[str, ...]
    missing_call_to_action_ids: tuple[str, ...]
    repeated_groups: tuple[ContentVariationGroup, ...]

    @property
    def complete_metadata(self) -> bool:
        """Return whether all content items carry role, format, channel, and CTA metadata."""
        return not any(
            (
                self.missing_role_ids,
                self.missing_format_ids,
                self.missing_channel_ids,
                self.missing_call_to_action_ids,
            )
        )
