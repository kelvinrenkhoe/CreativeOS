"""Generate deterministic image prompt specifications from storyboards."""

from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.image_prompt import (
    AspectRatio,
    ImagePromptError,
    ImagePromptSet,
    SceneImagePrompt,
    VisualStyle,
)
from models.storyboard import Storyboard


class ImagePromptGenerator:
    """Translate storyboard scenes into stable image prompt specifications."""

    def generate(
        self,
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
        storyboard: Storyboard,
        *,
        aspect_ratio: AspectRatio = AspectRatio.VERTICAL,
        visual_style: VisualStyle = VisualStyle.CINEMATIC,
    ) -> ImagePromptSet:
        """Return one deterministic prompt for every storyboard scene."""
        if deliverable.deliverable_type is not DeliverableType.IMAGE_PROMPT:
            raise ImagePromptError("deliverable must be an image prompt")
        campaign_ids = {brief.campaign_id, storyboard.campaign_id}
        if len(campaign_ids) != 1 or deliverable.deliverable_id.split("-week-")[0] != brief.campaign_id:
            raise ImagePromptError("brief, deliverable, and storyboard must share a campaign")

        prompts = tuple(
            SceneImagePrompt(
                prompt_id=f"{storyboard.storyboard_id}-scene-{scene.scene_number}",
                scene_number=scene.scene_number,
                subject=", ".join(scene.characters),
                action=scene.action,
                location=scene.location,
                composition=(
                    f"{scene.shot.value} composition with {scene.movement.value} camera intent"
                ),
                lighting=scene.lighting.value.replace("_", " "),
                mood=f"{scene.mood.value}; emotion: {scene.emotion}",
                wardrobe=f"Campaign-consistent wardrobe for {brief.artist}",
                props=("campaign-relevant practical props",),
                continuity_notes=(
                    f"Maintain the same character identity, wardrobe language, and visual tone; "
                    f"campaign tone: {brief.tone}"
                ),
                aspect_ratio=aspect_ratio,
                visual_style=visual_style,
                negative_constraints=(
                    "text overlays",
                    "watermarks",
                    "distorted anatomy",
                    "inconsistent character identity",
                ),
            )
            for scene in storyboard.scenes
        )

        return ImagePromptSet(
            prompt_set_id=f"{deliverable.deliverable_id}-prompts",
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=deliverable.campaign_week,
            storyboard_id=storyboard.storyboard_id,
            prompts=prompts,
        )
