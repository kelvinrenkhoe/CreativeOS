"""Read-only sequencing recommendations for campaign content inventories."""

from models.content_inventory_report import ContentInventoryReport, ContentVariationGroup
from models.content_sequence_recommendation import (
    ContentSequenceRecommendation,
    ContentSequenceRecommendationReport,
)
from services.content_inventory_inspection import ContentInventoryInspectionService


class ContentSequenceRecommendationService:
    """Recommend content variation improvements without mutating campaign state."""

    def __init__(self, inspection_service: ContentInventoryInspectionService) -> None:
        self.inspection_service = inspection_service

    def recommend(self) -> ContentSequenceRecommendationReport:
        """Return deterministic recommendations from the current inventory report."""
        return recommend_from_report(self.inspection_service.inspect())


def recommend_from_report(report: ContentInventoryReport) -> ContentSequenceRecommendationReport:
    """Build stable recommendations from content coverage and repetition signals."""
    recommendations: list[ContentSequenceRecommendation] = []

    missing_fields = (
        ("role", report.missing_role_ids),
        ("format", report.missing_format_ids),
        ("channel", report.missing_channel_ids),
        ("call-to-action", report.missing_call_to_action_ids),
    )
    for field_name, content_ids in missing_fields:
        if content_ids:
            recommendations.append(
                ContentSequenceRecommendation(
                    recommendation_id=f"complete-{field_name}",
                    summary=(
                        f"Complete {field_name} metadata before sequencing so "
                        "variation can be assessed."
                    ),
                    content_ids=content_ids,
                )
            )

    for index, group in enumerate(report.repeated_groups, start=1):
        recommendations.append(
            ContentSequenceRecommendation(
                recommendation_id=f"vary-repeated-signature-{index}",
                summary=(
                    "Vary at least one content dimension across these items: "
                    + ", ".join(_variation_dimensions(group))
                    + "."
                ),
                content_ids=group.content_ids,
            )
        )

    return ContentSequenceRecommendationReport(recommendations=tuple(recommendations))


def _variation_dimensions(group: ContentVariationGroup) -> tuple[str, ...]:
    """Return the dimensions that can be varied for a repeated signature."""
    return ("role", "format", "channel", "call-to-action")
