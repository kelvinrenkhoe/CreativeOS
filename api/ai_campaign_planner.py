"""API boundary for creator-facing AI campaign planning."""

from services.ai_campaign_plan import AICampaignPlan
from services.ai_campaign_planner import AICampaignPlanService


class AICampaignPlannerAPI:
    """Delegate campaign planning through an injectable service."""

    def __init__(self, service: AICampaignPlanService | None = None) -> None:
        self.service = service or AICampaignPlanService()

    def plan(self, campaign_name: str) -> AICampaignPlan:
        """Return one structured campaign plan."""
        return self.service.plan(campaign_name)
