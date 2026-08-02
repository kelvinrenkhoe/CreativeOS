"""Generate deterministic press and media packages from Creative Studio plans."""

from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.media import MediaChannel, MediaContext, MediaError, MediaGoal
from models.press import PressAsset, PressAssetType, PressPackage


class PressGenerator:
    """Build provider-neutral media assets without publishing side effects."""

    def generate(
        self,
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
    ) -> PressPackage:
        if deliverable.deliverable_type is not DeliverableType.PRESS_ARTICLE:
            raise MediaError("deliverable must be a press article")
        if not deliverable.deliverable_id.startswith(f"{brief.campaign_id}-"):
            raise MediaError("deliverable belongs to another campaign")

        subject = deliverable.source_item_id or brief.next_item_id or "the campaign story"
        call_to_action = f"Follow {brief.campaign_name} on {', '.join(brief.platforms)}."
        context = MediaContext(
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=deliverable.campaign_week,
            artist=brief.artist,
            audience=brief.audience,
            tone=brief.tone,
            objective=brief.objective,
            call_to_action=call_to_action,
        )
        assets = self._build_assets(context, subject, brief.story_context)
        return PressPackage(
            package_id=f"{deliverable.deliverable_id}-package",
            context=context,
            assets=assets,
        )

    @staticmethod
    def _build_assets(
        context: MediaContext,
        subject: str,
        story_context: str,
    ) -> tuple[PressAsset, ...]:
        campaign = context.campaign_name
        artist = context.artist
        objective = context.objective
        audience = context.audience
        tone = context.tone
        cta = context.call_to_action
        return (
            PressAsset(
                f"{context.campaign_id}-press-release",
                PressAssetType.PRESS_RELEASE,
                MediaChannel.PRESS,
                MediaGoal.COVERAGE,
                f"{artist} introduces {campaign}",
                f"{artist} introduces {campaign}, a campaign shaped by {story_context} "
                f"and created to {objective.lower()} The story centres on {subject} and "
                f"speaks to {audience.lower()} {cta}",
            ),
            PressAsset(
                f"{context.campaign_id}-blog-article",
                PressAssetType.BLOG_ARTICLE,
                MediaChannel.BLOG,
                MediaGoal.DISCOVERY,
                f"The story behind {campaign}",
                f"{campaign} explores {story_context} Through {subject}, {artist} presents "
                f"a {tone.lower()} message designed for {audience.lower()} {cta}",
            ),
            PressAsset(
                f"{context.campaign_id}-playlist-pitch",
                PressAssetType.PLAYLIST_PITCH,
                MediaChannel.PLAYLIST,
                MediaGoal.STREAMS,
                f"Playlist pitch: {campaign}",
                f"{campaign} pairs the voice of {artist} with a {tone.lower()} story about "
                f"{subject}. It is positioned for listeners seeking {audience.lower()} and "
                f"supports the campaign objective to {objective.lower()}",
            ),
            PressAsset(
                f"{context.campaign_id}-interview-pitch",
                PressAssetType.INTERVIEW_PITCH,
                MediaChannel.INTERVIEW,
                MediaGoal.INTERVIEW,
                f"Interview opportunity with {artist}",
                f"{artist} is available to discuss the inspiration behind {campaign}, the "
                f"role of {subject}, and how {story_context} shaped the campaign message.",
            ),
            PressAsset(
                f"{context.campaign_id}-artist-biography",
                PressAssetType.ARTIST_BIOGRAPHY,
                MediaChannel.EPK,
                MediaGoal.AWARENESS,
                f"About {artist}",
                f"{artist} creates story-led music campaigns that connect lived experience "
                f"with a {tone.lower()} voice. {campaign} continues that creative direction.",
            ),
            PressAsset(
                f"{context.campaign_id}-song-story",
                PressAssetType.SONG_STORY,
                MediaChannel.BLOG,
                MediaGoal.DISCOVERY,
                f"Campaign story: {campaign}",
                f"The story begins with {story_context} It develops through {subject} and "
                f"turns the campaign objective—to {objective.lower()}—into a human message.",
            ),
            PressAsset(
                f"{context.campaign_id}-media-kit-summary",
                PressAssetType.MEDIA_KIT_SUMMARY,
                MediaChannel.EPK,
                MediaGoal.COVERAGE,
                f"Media kit summary: {campaign}",
                f"Artist: {artist}. Campaign: {campaign}. Audience: {audience}. Tone: {tone}. "
                f"Primary story asset: {subject}. {cta}",
            ),
            PressAsset(
                f"{context.campaign_id}-quote-sheet",
                PressAssetType.QUOTE_SHEET,
                MediaChannel.PRESS,
                MediaGoal.COVERAGE,
                f"Quotes from {campaign}",
                f'“{campaign} is about turning pressure into purpose.” — {artist}\n\n'
                f'“The story of {subject} reminds us to keep moving.” — {artist}',
            ),
            PressAsset(
                f"{context.campaign_id}-press-headline",
                PressAssetType.PRESS_HEADLINE,
                MediaChannel.PRESS,
                MediaGoal.AWARENESS,
                f"{artist} brings a {tone.lower()} message to {campaign}",
                f"{artist} presents {campaign}, a story-led campaign centred on {subject}.",
            ),
            PressAsset(
                f"{context.campaign_id}-social-press-snippet",
                PressAssetType.SOCIAL_PRESS_SNIPPET,
                MediaChannel.SOCIAL,
                MediaGoal.DISCOVERY,
                f"Discover {campaign}",
                f"A {tone.lower()} new chapter from {artist}, shaped by {story_context} {cta}",
            ),
        )
