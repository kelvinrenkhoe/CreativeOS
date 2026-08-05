"""API boundary for creator-facing AI campaign planning."""

from ai.provider import AIProvider
from services.ai_campaign_plan import AICampaignPlan
from services.ai_campaign_planner import AICampaignPlanService


class AICampaignPlannerAPI:
    """Delegate campaign planning through an injectable service or provider."""

    def __init__(
        self,
        service: AICampaignPlanService | None = None,
        *,
        provider: AIProvider | None = None,
    ) -> None:
        if service is not None and provider is not None:
            raise ValueError("service and provider cannot both be supplied")
        self.service = service or AICampaignPlanService(provider)

    def plan(self, campaign_name: str) -> AICampaignPlan:
        """Return one structured campaign plan."""
        return self.service.plan(campaign_name)
