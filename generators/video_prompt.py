"""Generate deterministic video directions from storyboards and image prompts."""

from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.image_prompt import ImagePromptSet
from models.storyboard import Storyboard
from models.video_prompt import (
    ContinuityMode,
    MotionIntensity,
    Pacing,
    SceneVideoPrompt,
    VideoPromptError,
    VideoPromptSet,
)


class VideoPromptGenerator:
    """Translate storyboard scenes into stable provider-neutral video directions."""

    def generate(
        self,
        brief: CreativeBrief,
        deliverable: CreativeDeliverable,
        storyboard: Storyboard,
        image_prompts: ImagePromptSet,
        *,
        pacing: Pacing = Pacing.MODERATE,
        motion_intensity: MotionIntensity = MotionIntensity.BALANCED,
        continuity_mode: ContinuityMode = ContinuityMode.STRICT,
    ) -> VideoPromptSet:
        """Return one deterministic video prompt for each storyboard scene."""
        if deliverable.deliverable_type is not DeliverableType.VIDEO_PROMPT:
            raise VideoPromptError("deliverable must be a video prompt")

        deliverable_campaign = deliverable.deliverable_id.split("-week-")[0]
        campaign_ids = {
            brief.campaign_id,
            storyboard.campaign_id,
            image_prompts.campaign_id,
            deliverable_campaign,
        }
        if len(campaign_ids) != 1:
            raise VideoPromptError("all inputs must share a campaign")
        if image_prompts.storyboard_id != storyboard.storyboard_id:
            raise VideoPromptError("image prompts must belong to the storyboard")
        if len(image_prompts.prompts) != len(storyboard.scenes):
            raise VideoPromptError("image prompts must match storyboard scenes")

        prompts = tuple(
            self._build_scene_prompt(
                scene,
                image_prompt.prompt_id,
                storyboard.storyboard_id,
                brief,
                pacing,
                motion_intensity,
            )
            for scene, image_prompt in zip(
                storyboard.scenes,
                image_prompts.prompts,
                strict=True,
            )
        )

        return VideoPromptSet(
            prompt_set_id=f"{deliverable.deliverable_id}-prompts",
            campaign_id=brief.campaign_id,
            campaign_name=brief.campaign_name,
            campaign_week=deliverable.campaign_week,
            storyboard_id=storyboard.storyboard_id,
            image_prompt_set_id=image_prompts.prompt_set_id,
            continuity_mode=continuity_mode,
            prompts=prompts,
        )

    @staticmethod
    def _build_scene_prompt(
        scene,
        visual_reference_prompt_id: str,
        storyboard_id: str,
        brief: CreativeBrief,
        pacing: Pacing,
        motion_intensity: MotionIntensity,
    ) -> SceneVideoPrompt:
        return SceneVideoPrompt(
            prompt_id=f"{storyboard_id}-scene-{scene.scene_number}-video",
            scene_number=scene.scene_number,
            duration_seconds=scene.duration_seconds,
            visual_reference_prompt_id=visual_reference_prompt_id,
            camera_direction=(
                f"Use a {scene.shot.value} shot with {scene.movement.value} movement"
            ),
            subject_motion=f"Animate the characters performing: {scene.action}",
            environmental_motion=(
                f"Add subtle natural movement appropriate to {scene.location}"
            ),
            transition_direction=(
                f"End with a {scene.transition.value} transition timed to the final beat"
            ),
            music_alignment=f"Align the scene to: {scene.music_cue}",
            continuity_notes=(
                "Preserve character identity, wardrobe, location language, lighting, and "
                f"campaign tone across scenes; tone: {brief.tone}"
            ),
            pacing=pacing,
            motion_intensity=motion_intensity,
            provider_instructions=(
                "Generate a coherent cinematic clip without text overlays, watermarks, "
                "identity drift, abrupt motion, or anatomy distortion."
            ),
        )
