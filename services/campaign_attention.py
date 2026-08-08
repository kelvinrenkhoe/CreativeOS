"""Deterministic prioritisation for operational campaign attention."""

from dataclasses import dataclass

from services.campaign_workspace import CampaignWorkspaceReport


@dataclass(frozen=True, slots=True)
class CampaignAttentionItem:
    """One explainable operational item requiring campaign attention."""

    item_id: str
    kind: str
    priority: int
    reason: str


class CampaignAttentionService:
    """Prioritise workspace attention using explicit deterministic rules."""

    def prioritise(
        self,
        report: CampaignWorkspaceReport,
    ) -> tuple[CampaignAttentionItem, ...]:
        """Return stable priority-ordered attention items without mutating state."""
        items: list[CampaignAttentionItem] = []

        for action_id in report.blocked_action_ids:
            items.append(
                CampaignAttentionItem(
                    item_id=action_id,
                    kind="blocked-action",
                    priority=1,
                    reason=(
                        "Execution is blocked and cannot progress until this action "
                        "is resolved."
                    ),
                )
            )

        for asset_id in report.asset_readiness.missing_location:
            items.append(
                CampaignAttentionItem(
                    item_id=asset_id,
                    kind="asset-location",
                    priority=2,
                    reason="An approved or published asset is missing a usable artifact location.",
                )
            )

        for content_id in report.content_gap_ids:
            items.append(
                CampaignAttentionItem(
                    item_id=content_id,
                    kind="content-metadata",
                    priority=3,
                    reason=(
                        "Content metadata is incomplete and reduces production or "
                        "sequencing readiness."
                    ),
                )
            )

        return tuple(
            sorted(
                items,
                key=lambda item: (item.priority, item.kind, item.item_id),
            )
        )
