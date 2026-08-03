"""Deterministic campaign improvement recommendations."""

from dataclasses import dataclass

from models.campaign_recommendation import (
    CampaignRecommendation,
    CampaignRecommendations,
)
from models.doctor import DoctorCheck, DoctorReport


@dataclass(frozen=True)
class RecommendationRule:
    """Static recommendation mapping for a Doctor check."""

    title: str
    detail: str
    action_template: str | None
    impact: str
    priority: int


RULES: dict[str, RecommendationRule] = {
    "Release date": RecommendationRule(
        title="Configure the campaign release date",
        detail=("Add a valid ISO-8601 release date so the rollout can be scheduled and validated."),
        action_template=(
            "Update campaigns/{campaign_slug}/campaign.yaml with release_date: YYYY-MM-DD"
        ),
        impact="high",
        priority=1,
    ),
    "Streaming link": RecommendationRule(
        title="Add a streaming or smart link",
        detail=(
            "Add a Spotify URL or smart link so campaign content can "
            "direct listeners to the release."
        ),
        action_template=(
            "Update campaigns/{campaign_slug}/campaign.yaml with spotify or smart_link"
        ),
        impact="high",
        priority=1,
    ),
    "Artwork": RecommendationRule(
        title="Add final campaign artwork",
        detail=("Add approved release artwork to support social, press and distribution activity."),
        action_template=("Add artwork files to campaigns/{campaign_slug}/assets/artwork/"),
        impact="high",
        priority=1,
    ),
    "Video assets": RecommendationRule(
        title="Prepare short-form campaign videos",
        detail=(
            "Create varied short-form video assets for TikTok, Instagram "
            "Reels, YouTube Shorts and other campaign placements."
        ),
        action_template=("Add video files to campaigns/{campaign_slug}/assets/videos/"),
        impact="high",
        priority=1,
    ),
    "Content calendar": RecommendationRule(
        title="Create a campaign content calendar",
        detail=(
            "Plan publishing dates, platforms and content formats across the campaign timeline."
        ),
        action_template=("Complete campaigns/{campaign_slug}/schedule/content-calendar.md"),
        impact="high",
        priority=1,
    ),
    "Press release": RecommendationRule(
        title="Prepare the campaign press release",
        detail=(
            "Create a press release that communicates the release story, "
            "artist context and key campaign message."
        ),
        action_template=("Complete campaigns/{campaign_slug}/press/press-release.md"),
        impact="medium",
        priority=2,
    ),
    "Radio outreach": RecommendationRule(
        title="Build the radio outreach list",
        detail=(
            "Add target stations, contacts and outreach status so radio "
            "promotion can be managed consistently."
        ),
        action_template=("Complete campaigns/{campaign_slug}/radio/stations.csv"),
        impact="medium",
        priority=2,
    ),
    "Platforms": RecommendationRule(
        title="Configure campaign platforms",
        detail=(
            "Select the social and streaming platforms that the campaign will actively support."
        ),
        action_template=("Update campaigns/{campaign_slug}/campaign.yaml with target platforms"),
        impact="medium",
        priority=2,
    ),
    "Campaign goals": RecommendationRule(
        title="Define measurable campaign goals",
        detail=(
            "Add measurable goals for streams, playlists, radio, creators "
            "or other campaign outcomes."
        ),
        action_template=("Update campaigns/{campaign_slug}/campaign.yaml with campaign goals"),
        impact="medium",
        priority=2,
    ),
    "Campaign workspace": RecommendationRule(
        title="Create the campaign workspace",
        detail=("Create the campaign directory and standard CreativeOS campaign structure."),
        action_template='creativeos campaign create "{campaign_name}"',
        impact="high",
        priority=1,
    ),
    "Campaign manifest": RecommendationRule(
        title="Create the campaign manifest",
        detail=(
            "Create campaign.yaml with campaign identity, release, platform and goal information."
        ),
        action_template='creativeos campaign create "{campaign_name}"',
        impact="high",
        priority=1,
    ),
    "Manifest configuration": RecommendationRule(
        title="Repair the campaign manifest",
        detail=("Correct campaign.yaml so it contains valid CreativeOS campaign configuration."),
        action_template=("Review campaigns/{campaign_slug}/campaign.yaml"),
        impact="high",
        priority=1,
    ),
}


class CampaignRecommendationsService:
    """Generate ordered recommendations from Campaign Doctor findings."""

    def recommend(
        self,
        campaign_name: str,
        report: DoctorReport,
    ) -> CampaignRecommendations:
        """Return deterministic recommendations for failed checks."""
        clean_name = campaign_name.strip()
        if not clean_name:
            raise ValueError("campaign_name must not be empty")

        campaign_slug = self._slugify(clean_name)

        recommendations = tuple(
            sorted(
                (
                    recommendation
                    for check in report.checks
                    if not check.passed
                    for recommendation in (
                        self._recommendation_for(
                            check,
                            campaign_name=clean_name,
                            campaign_slug=campaign_slug,
                        ),
                    )
                    if recommendation is not None
                ),
                key=lambda item: (
                    item.priority,
                    item.category,
                    item.source_check,
                ),
            )
        )

        return CampaignRecommendations(
            campaign_name=clean_name,
            items=recommendations,
        )

    @staticmethod
    def _recommendation_for(
        check: DoctorCheck,
        *,
        campaign_name: str,
        campaign_slug: str,
    ) -> CampaignRecommendation | None:
        rule = RULES.get(check.name)
        if rule is None:
            return None

        action = (
            rule.action_template.format(
                campaign_name=campaign_name,
                campaign_slug=campaign_slug,
            )
            if rule.action_template is not None
            else None
        )

        return CampaignRecommendation(
            category=check.category,
            source_check=check.name,
            title=rule.title,
            detail=rule.detail,
            action=action,
            impact=rule.impact,
            priority=rule.priority,
        )

    @staticmethod
    def _slugify(value: str) -> str:
        return "-".join(
            part
            for part in "".join(
                character.lower() if character.isalnum() else " " for character in value
            ).split()
            if part
        )
