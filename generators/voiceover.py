"""Generate deterministic scene-aligned voice-over scripts."""

from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.storyboard import SceneMood, Storyboard, StoryboardScene
from models.voiceover import (
    NarrationPace,
    VoiceoverError,
    VoiceoverScript,
    VoiceoverSegment,
    VoiceoverStyle,
)


class VoiceoverGenerator:
    """Build provider-neutral narration aligned with storyboard scenes."""

    def generate(
        self,
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
        storyboard: Storyboard,
    ) -> VoiceoverScript:
        if deliverable.deliverable_type is not DeliverableType.VOICEOVER:
            raise VoiceoverError("deliverable must be a voiceover")
        if not deliverable.deliverable_id.startswith(f"{brief.campaign_id}-"):
            raise VoiceoverError("deliverable belongs to another campaign")
        if storyboard.campaign_id != brief.campaign_id:
            raise VoiceoverError("brief and storyboard must share a campaign")
        if storyboard.campaign_week != deliverable.campaign_week:
            raise VoiceoverError("storyboard and deliverable must share a campaign week")

        segments = tuple(
            self._build_segment(brief, scene, len(storyboard.scenes)) for scene in storyboard.scenes
        )
        call_to_action = storyboard.call_to_action
        return VoiceoverScript(
            script_id=f"{deliverable.deliverable_id}-script",
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=deliverable.campaign_week,
            title=f"{brief.campaign_name} — Week {deliverable.campaign_week} Voice-over",
            tone=brief.tone,
            audience=brief.audience,
            call_to_action=call_to_action,
            segments=segments,
        )

    @staticmethod
    def _build_segment(
        brief: CreativeBrief,
        scene: StoryboardScene,
        scene_count: int,
    ) -> VoiceoverSegment:
        if scene.scene_number == 1:
            narration = "Every journey begins with a moment that asks us to choose."
        elif scene.scene_number == scene_count:
            narration = f"This is {brief.campaign_name}: keep moving, and never lose your guard."
        else:
            narration = (
                f"Through {scene.action.lower()}, the story turns {scene.emotion.lower()} "
                f"into a reason to continue."
            )

        style, pace = _delivery_for_mood(scene.mood)
        emphasis = _emphasis_terms(narration, brief.campaign_name)
        return VoiceoverSegment(
            scene_number=scene.scene_number,
            duration_seconds=scene.duration_seconds,
            narration=narration,
            style=style,
            pace=pace,
            emphasis=emphasis,
            pause_after_seconds=0.5 if scene.scene_number < scene_count else 1.0,
        )


def _delivery_for_mood(mood: SceneMood) -> tuple[VoiceoverStyle, NarrationPace]:
    mapping = {
        SceneMood.REFLECTIVE: (VoiceoverStyle.REFLECTIVE, NarrationPace.SLOW),
        SceneMood.DETERMINED: (VoiceoverStyle.MOTIVATIONAL, NarrationPace.MEASURED),
        SceneMood.HOPEFUL: (VoiceoverStyle.CONVERSATIONAL, NarrationPace.MODERATE),
        SceneMood.TRIUMPHANT: (VoiceoverStyle.CINEMATIC, NarrationPace.ENERGETIC),
    }
    return mapping[mood]


def _emphasis_terms(narration: str, campaign_name: str) -> tuple[str, ...]:
    terms = []
    if campaign_name.lower() in narration.lower():
        terms.append(campaign_name)
    for candidate in ("choose", "continue", "keep moving", "never lose your guard"):
        if candidate in narration.lower():
            terms.append(candidate)
    return tuple(terms)
