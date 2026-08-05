"""Build deterministic AI campaign plans behind a stable service contract."""

from services.ai_campaign_plan import (
    AICampaignObjective,
    AICampaignPlan,
    AICampaignTask,
    AICampaignWeek,
)


class AICampaignPlanService:
    """Return a deterministic rollout until provider integration is added."""

    def plan(self, campaign_name: str) -> AICampaignPlan:
        """Build a four-week creator-facing rollout plan."""
        name = campaign_name.strip()
        if not name:
            raise ValueError("campaign_name must not be empty")

        return AICampaignPlan(
            campaign_name=name,
            duration_days=28,
            objectives=(
                AICampaignObjective("Increase release awareness"),
                AICampaignObjective("Grow engaged listeners"),
                AICampaignObjective("Convert attention into streams and saves"),
            ),
            weeks=(
                AICampaignWeek(
                    number=1,
                    objective="Introduce the campaign and build curiosity",
                    tasks=(
                        AICampaignTask("Campaign announcement", "Introduce the release story."),
                        AICampaignTask("Cover reveal", "Share the artwork and central message."),
                    ),
                ),
                AICampaignWeek(
                    number=2,
                    objective="Build recognition around the strongest hook",
                    tasks=(
                        AICampaignTask("Hook videos", "Publish short vertical hook variations."),
                        AICampaignTask("Behind the scenes", "Show the creative process."),
                    ),
                ),
                AICampaignWeek(
                    number=3,
                    objective="Drive discovery and release intent",
                    tasks=(
                        AICampaignTask("Playlist outreach", "Pitch relevant playlists and DJs."),
                        AICampaignTask("Fan prompt", "Invite listeners to react or participate."),
                    ),
                ),
                AICampaignWeek(
                    number=4,
                    objective="Sustain momentum and deepen connection",
                    tasks=(
                        AICampaignTask("Performance content", "Share a live or stripped-back clip."),
                        AICampaignTask("Thank-you post", "Celebrate listeners and early supporters."),
                    ),
                ),
            ),
        )
