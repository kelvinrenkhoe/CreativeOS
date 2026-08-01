"""Build deterministic creative briefs from campaign planning context."""

from models.campaign_recovery import RecoveryPlan
from models.creative_brief import (
    CreativeBrief,
    CreativeBriefBlockedItem,
    CreativeBriefError,
    CreativeBriefRecovery,
    CreativeBriefRequest,
)
from services.campaign_execution import CampaignExecutionState
from services.campaign_memory import CampaignMemory


class CreativeBriefService:
    """Assemble read-only campaign context for downstream generators."""

    def build(
        self,
        request: CreativeBriefRequest,
        execution_state: CampaignExecutionState,
        memory: CampaignMemory,
        recovery_plan: RecoveryPlan | None = None,
    ) -> CreativeBrief:
        """Return a deterministic creative brief without side effects."""
        if execution_state.campaign_id != request.campaign_id:
            raise CreativeBriefError("execution state belongs to another campaign")
        if recovery_plan is not None and recovery_plan.campaign_id != request.campaign_id:
            raise CreativeBriefError("recovery plan belongs to another campaign")

        blocked_items = tuple(
            CreativeBriefBlockedItem(
                item_id=item.item_id,
                unmet_prerequisite_ids=item.unmet_prerequisite_ids,
            )
            for item in execution_state.blocked_items
        )

        recovery = None
        if recovery_plan is not None:
            recovery = CreativeBriefRecovery(
                changed=recovery_plan.changed,
                recovered_item_ids=recovery_plan.recovered_item_ids,
                fixed_milestone_ids=recovery_plan.fixed_milestone_ids,
                moved_item_ids=tuple(action.item_id for action in recovery_plan.actions),
            )

        return CreativeBrief(
            campaign_id=request.campaign_id,
            campaign_name=request.campaign_name,
            artist=request.artist,
            objective=request.objective,
            audience=request.audience,
            tone=request.tone,
            platforms=request.platforms,
            knowledge=request.knowledge or "No artist or song knowledge was supplied.",
            story_context=request.story_context or "No story context was supplied.",
            memory=memory.render(),
            completed_item_ids=execution_state.completed_item_ids,
            ready_item_ids=execution_state.ready_item_ids,
            blocked_items=blocked_items,
            next_item_id=execution_state.next_item_id,
            next_reason=execution_state.next_reason,
            recovery=recovery,
        )
