"""Generate deterministic cinematic storyboards from Creative Studio plans."""

from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.storyboard import (
    CameraMovement,
    CameraShot,
    LightingStyle,
    SceneMood,
    SceneTransition,
    Storyboard,
    StoryboardError,
    StoryboardScene,
)


class StoryboardGenerator:
    """Build a stable storyboard specification without provider calls."""

    def generate(
        self,
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
    ) -> Storyboard:
        if deliverable.deliverable_type is not DeliverableType.STORYBOARD:
            raise StoryboardError("deliverable must be a storyboard")
        if not deliverable.deliverable_id.startswith(f"{brief.campaign_id}-"):
            raise StoryboardError("deliverable belongs to another campaign")

        subject = deliverable.source_item_id or "campaign story"
        cta = f"Follow the {brief.campaign_name} campaign on {', '.join(brief.platforms)}."
        scenes = (
            StoryboardScene(
                1,
                4,
                "Opening environment",
                (brief.artist,),
                f"Establish the world around {subject}.",
                "Quiet anticipation",
                CameraShot.WIDE,
                CameraMovement.STATIC,
                LightingStyle.NATURAL,
                SceneMood.REFLECTIVE,
                "Instrumental introduction",
                SceneTransition.CUT,
            ),
            StoryboardScene(
                2,
                5,
                "Primary story location",
                (brief.artist,),
                f"Show the central struggle connected to {brief.objective}.",
                "Pressure turning into resolve",
                CameraShot.MEDIUM,
                CameraMovement.TRACK,
                LightingStyle.LOW_KEY,
                SceneMood.DETERMINED,
                "Rhythm and vocal build",
                SceneTransition.MATCH_CUT,
            ),
            StoryboardScene(
                3,
                5,
                "Turning-point location",
                (brief.artist,),
                f"Reveal a hopeful change for {brief.audience}.",
                "Renewed confidence",
                CameraShot.CLOSE_UP,
                CameraMovement.PUSH_IN,
                LightingStyle.GOLDEN_HOUR,
                SceneMood.HOPEFUL,
                "Hook or chorus enters",
                SceneTransition.DISSOLVE,
            ),
            StoryboardScene(
                4,
                3,
                "Campaign end card",
                (brief.artist,),
                cta,
                "Confident invitation",
                CameraShot.DETAIL,
                CameraMovement.STATIC,
                LightingStyle.PRACTICAL,
                SceneMood.TRIUMPHANT,
                "Final lyric and resolve",
                SceneTransition.FADE,
            ),
        )
        return Storyboard(
            storyboard_id=f"{deliverable.deliverable_id}-storyboard",
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=deliverable.campaign_week,
            title=f"{brief.campaign_name} — Week {deliverable.campaign_week}",
            objective=brief.objective,
            audience=brief.audience,
            tone=brief.tone,
            platforms=brief.platforms,
            call_to_action=cta,
            scenes=scenes,
        )
