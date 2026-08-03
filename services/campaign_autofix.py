"""Plan-only campaign auto-fix classification."""

from dataclasses import dataclass

from models.campaign_fix import CampaignFix, CampaignFixPlan
from models.campaign_recommendation import (
    CampaignRecommendation,
    CampaignRecommendations,
)


@dataclass(frozen=True)
class FixRule:
    """Static mapping from a recommendation source to a proposed fix."""

    kind: str
    operation: str
    target_template: str | None
    detail: str


RULES: dict[str, FixRule] = {
    "Artwork": FixRule(
        kind="automatic",
        operation="ensure-directory",
        target_template="campaigns/{campaign_slug}/assets/artwork",
        detail="Ensure the campaign artwork directory exists.",
    ),
    "Video assets": FixRule(
        kind="automatic",
        operation="ensure-directory",
        target_template="campaigns/{campaign_slug}/assets/videos",
        detail="Ensure the campaign video directory exists.",
    ),
    "Content calendar": FixRule(
        kind="automatic",
        operation="create-file",
        target_template=("campaigns/{campaign_slug}/schedule/content-calendar.md"),
        detail="Create the standard empty content-calendar template.",
    ),
    "Press release": FixRule(
        kind="automatic",
        operation="create-file",
        target_template="campaigns/{campaign_slug}/press/press-release.md",
        detail="Create the standard empty press-release template.",
    ),
    "Radio outreach": FixRule(
        kind="automatic",
        operation="create-file",
        target_template="campaigns/{campaign_slug}/radio/stations.csv",
        detail="Create the standard radio outreach CSV template.",
    ),
    "Release date": FixRule(
        kind="manual",
        operation="update-configuration",
        target_template="campaigns/{campaign_slug}/campaign.yaml",
        detail="A release date must be supplied by the user.",
    ),
    "Streaming link": FixRule(
        kind="manual",
        operation="update-configuration",
        target_template="campaigns/{campaign_slug}/campaign.yaml",
        detail="A Spotify or smart link must be supplied by the user.",
    ),
    "Platforms": FixRule(
        kind="manual",
        operation="update-configuration",
        target_template="campaigns/{campaign_slug}/campaign.yaml",
        detail="Target platforms require a campaign decision.",
    ),
    "Campaign goals": FixRule(
        kind="manual",
        operation="update-configuration",
        target_template="campaigns/{campaign_slug}/campaign.yaml",
        detail="Campaign goals require user-defined targets.",
    ),
    "Campaign workspace": FixRule(
        kind="automatic",
        operation="run-command",
        target_template=None,
        detail="Create the standard campaign workspace.",
    ),
    "Campaign manifest": FixRule(
        kind="unsupported",
        operation="unsupported",
        target_template="campaigns/{campaign_slug}/campaign.yaml",
        detail=("Manifest repair is not safe until the required campaign values are known."),
    ),
    "Manifest configuration": FixRule(
        kind="unsupported",
        operation="unsupported",
        target_template="campaigns/{campaign_slug}/campaign.yaml",
        detail="Invalid manifest content requires review before repair.",
    ),
}


class CampaignAutoFixPlanner:
    """Convert campaign recommendations into a non-mutating fix plan."""

    def plan(
        self,
        recommendations: CampaignRecommendations,
    ) -> CampaignFixPlan:
        """Return an ordered plan without applying any fix."""
        campaign_name = recommendations.campaign_name.strip()
        campaign_slug = self._slugify(campaign_name)

        fixes = tuple(
            sorted(
                (
                    self._to_fix(
                        recommendation,
                        campaign_name=campaign_name,
                        campaign_slug=campaign_slug,
                    )
                    for recommendation in recommendations.items
                ),
                key=lambda fix: (
                    fix.priority,
                    self._kind_order(fix.kind),
                    fix.category,
                    fix.source_check,
                ),
            )
        )

        return CampaignFixPlan(
            campaign_name=campaign_name,
            fixes=fixes,
        )

    @staticmethod
    def _to_fix(
        recommendation: CampaignRecommendation,
        *,
        campaign_name: str,
        campaign_slug: str,
    ) -> CampaignFix:
        rule = RULES.get(
            recommendation.source_check,
            FixRule(
                kind="unsupported",
                operation="unsupported",
                target_template=None,
                detail="No safe deterministic fix is currently supported.",
            ),
        )

        target = (
            rule.target_template.format(
                campaign_name=campaign_name,
                campaign_slug=campaign_slug,
            )
            if rule.target_template is not None
            else recommendation.action
        )

        return CampaignFix(
            category=recommendation.category,
            source_check=recommendation.source_check,
            title=recommendation.title,
            kind=rule.kind,
            operation=rule.operation,
            target=target,
            detail=rule.detail,
            priority=recommendation.priority,
        )

    @staticmethod
    def _kind_order(kind: str) -> int:
        return {
            "automatic": 0,
            "manual": 1,
            "unsupported": 2,
        }[kind]

    @staticmethod
    def _slugify(value: str) -> str:
        return "-".join(
            part
            for part in "".join(
                character.lower() if character.isalnum() else " " for character in value
            ).split()
            if part
        )
