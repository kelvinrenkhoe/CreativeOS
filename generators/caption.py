"""Generate deterministic platform-aware captions with repetition controls."""

from models.caption import (
    CaptionError,
    CaptionPlatform,
    CaptionRequest,
    CaptionSet,
    CaptionStructure,
    CaptionVariant,
)
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType


_HOOKS = (
    "Some seasons test how firmly you can stand.",
    "The moment you nearly stop can become the moment you rise.",
    "Strength is not always loud.",
    "What keeps you moving when the road becomes difficult?",
    "This is for everyone choosing not to lose guard.",
)
_CTAS = (
    "Follow the journey and stay ready for the next chapter.",
    "Share this with someone who needs the message today.",
    "Save this moment and keep moving with us.",
    "Join the story and listen when the song arrives.",
    "Keep your guard up and pass the message on.",
)
_ANGLES = (
    "quiet resilience",
    "hope after pressure",
    "determination through uncertainty",
    "shared encouragement",
    "personal transformation",
)
_STRUCTURES = (
    CaptionStructure.HOOK_STORY_CTA,
    CaptionStructure.QUESTION_INSIGHT_CTA,
    CaptionStructure.STATEMENT_CONTEXT_CTA,
    CaptionStructure.MOMENT_MESSAGE_CTA,
    CaptionStructure.SHORT_HOOK_CTA,
)
_HASHTAGS = (
    "#NoLoseGuard",
    "#KelvinRankie",
    "#Afrobeats",
    "#KeepMoving",
    "#NewMusic",
)


class CaptionGenerator:
    """Create stable caption variants without provider or publishing side effects."""

    def generate(
        self,
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
        request: CaptionRequest,
    ) -> CaptionSet:
        if deliverable.deliverable_type is not DeliverableType.CAPTION:
            raise CaptionError("deliverable must be a caption")

        deliverable_campaign = deliverable.deliverable_id.split("-week-")[0]
        if deliverable_campaign != brief.campaign_id:
            raise CaptionError("brief and deliverable must share a campaign")

        history = request.history
        hooks = _available(_HOOKS, history.hooks, "hooks")
        calls_to_action = _available(_CTAS, history.calls_to_action, "calls to action")
        angles = _available(_ANGLES, history.emotional_angles, "emotional angles")
        structures = tuple(item for item in _STRUCTURES if item not in history.structures)
        if not structures:
            raise CaptionError("no unused caption structures are available")
        hashtags = tuple(item for item in _HASHTAGS if item not in history.hashtags)

        variants = tuple(
            self._build_variant(
                brief,
                deliverable,
                platform,
                hooks[index % len(hooks)],
                angles[index % len(angles)],
                calls_to_action[index % len(calls_to_action)],
                structures[index % len(structures)],
                hashtags,
            )
            for index, platform in enumerate(request.platforms)
        )

        return CaptionSet(
            caption_set_id=f"{deliverable.deliverable_id}-variants",
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=deliverable.campaign_week,
            variants=variants,
        )

    @staticmethod
    def _build_variant(
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
        platform: CaptionPlatform,
        hook: str,
        emotional_angle: str,
        call_to_action: str,
        structure: CaptionStructure,
        available_hashtags: tuple[str, ...],
    ) -> CaptionVariant:
        source = deliverable.source_item_id or brief.next_item_id or "the campaign story"
        body = (
            f"{brief.campaign_name} carries a {emotional_angle} message for "
            f"{brief.audience.lower()} Through {source}, the campaign focuses on "
            f"{brief.objective.lower()} The voice remains {brief.tone.lower()}"
        )
        hashtag_limit = 0 if platform is CaptionPlatform.WHATSAPP else 2
        if platform is CaptionPlatform.INSTAGRAM:
            hashtag_limit = 4
        elif platform is CaptionPlatform.TIKTOK:
            hashtag_limit = 3

        return CaptionVariant(
            caption_id=f"{deliverable.deliverable_id}-{platform.value}",
            platform=platform,
            structure=structure,
            hook=hook,
            emotional_angle=emotional_angle,
            body=body,
            call_to_action=call_to_action,
            hashtags=available_hashtags[:hashtag_limit],
        )


def _available(
    candidates: tuple[str, ...],
    blocked: tuple[str, ...],
    label: str,
) -> tuple[str, ...]:
    values = tuple(item for item in candidates if item not in blocked)
    if not values:
        raise CaptionError(f"no unused {label} are available")
    return values
