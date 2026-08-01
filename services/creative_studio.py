"""Plan deterministic Creative Studio deliverables from one creative brief."""

from models.creative_brief import CreativeBrief
from models.creative_studio import (
    CreativeDeliverable,
    CreativeStudioError,
    StudioOutput,
    StudioRequest,
)


class CreativeStudioService:
    """Convert one creative brief into an ordered weekly creative package."""

    def build(self, brief: CreativeBrief, request: StudioRequest) -> StudioOutput:
        """Return a deterministic plan without provider or persistence side effects."""
        if brief.campaign_id != request.campaign_id:
            raise CreativeStudioError("creative brief belongs to another campaign")

        source_item_id = brief.next_item_id
        deliverables = tuple(
            CreativeDeliverable(
                deliverable_id=(
                    f"{request.campaign_id}-week-{request.campaign_week}-{deliverable_type.value}"
                ),
                deliverable_type=deliverable_type,
                campaign_week=request.campaign_week,
                objective=brief.objective,
                audience=brief.audience,
                tone=brief.tone,
                platforms=brief.platforms,
                source_item_id=source_item_id,
            )
            for deliverable_type in request.deliverable_types
        )

        return StudioOutput(
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=request.campaign_week,
            deliverables=deliverables,
        )
