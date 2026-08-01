"""Tests for deterministic image prompt generation."""

from dataclasses import FrozenInstanceError

import pytest

from generators.image_prompt import ImagePromptGenerator
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.image_prompt import AspectRatio, ImagePromptError, VisualStyle
from models.storyboard import (
    CameraMovement,
    CameraShot,
    LightingStyle,
    SceneMood,
    SceneTransition,
    Storyboard,
    StoryboardScene,
)


def brief(campaign_id: str = "no-lose-guard") -> CreativeBrief:
    return CreativeBrief(
        campaign_id=campaign_id,
        campaign_name="No Lose Guard",
        artist="Kelvin Rankie",
        objective="Build anticipation.",
        audience="Afrobeats listeners.",
        tone="Hopeful and cinematic.",
        platforms=("instagram", "tiktok"),
        knowledge="A song about perseverance.",
        story_context="A worker walks into sunrise.",
        memory="No campaign assets have been generated yet.",
        completed_item_ids=(),
        ready_item_ids=("storyboard",),
        blocked_items=(),
        next_item_id="storyboard",
        next_reason="Ready.",
        recovery=None,
    )


def deliverable(
    deliverable_type: DeliverableType = DeliverableType.IMAGE_PROMPT,
) -> CreativeDeliverable:
    return CreativeDeliverable(
        deliverable_id=f"no-lose-guard-week-3-{deliverable_type.value}",
        deliverable_type=deliverable_type,
        campaign_week=3,
        objective="Build anticipation.",
        audience="Afrobeats listeners.",
        tone="Hopeful and cinematic.",
        platforms=("instagram", "tiktok"),
        source_item_id="storyboard",
    )


def storyboard(campaign_id: str = "no-lose-guard") -> Storyboard:
    scenes = (
        StoryboardScene(
            scene_number=1,
            duration_seconds=5,
            location="Night-shift exit",
            characters=("Kelvin",),
            action="Walks into the early morning air.",
            emotion="Tired but focused.",
            shot=CameraShot.WIDE,
            movement=CameraMovement.TRACK,
            lighting=LightingStyle.GOLDEN_HOUR,
            mood=SceneMood.REFLECTIVE,
            music_cue="Instrumental intro.",
            transition=SceneTransition.CUT,
        ),
        StoryboardScene(
            scene_number=2,
            duration_seconds=5,
            location="Quiet London street",
            characters=("Kelvin",),
            action="Raises his head and keeps walking.",
            emotion="Determined.",
            shot=CameraShot.CLOSE_UP,
            movement=CameraMovement.PUSH_IN,
            lighting=LightingStyle.NATURAL,
            mood=SceneMood.HOPEFUL,
            music_cue="Hook begins.",
            transition=SceneTransition.FADE,
        ),
    )
    return Storyboard(
        storyboard_id=f"{campaign_id}-week-3-storyboard",
        campaign_id=campaign_id,
        campaign_name="No Lose Guard",
        campaign_week=3,
        title="Keep Moving",
        objective="Build anticipation.",
        audience="Afrobeats listeners.",
        tone="Hopeful and cinematic.",
        platforms=("instagram", "tiktok"),
        call_to_action="Pre-save No Lose Guard.",
        scenes=scenes,
    )


def test_generates_one_prompt_per_storyboard_scene() -> None:
    result = ImagePromptGenerator().generate(brief(), deliverable(), storyboard())

    assert len(result.prompts) == 2
    assert tuple(prompt.scene_number for prompt in result.prompts) == (1, 2)
    assert result.prompts[0].location == "Night-shift exit"
    assert result.prompts[1].prompt_id.endswith("scene-2")


def test_output_is_deterministic() -> None:
    generator = ImagePromptGenerator()

    first = generator.generate(brief(), deliverable(), storyboard())
    second = generator.generate(brief(), deliverable(), storyboard())

    assert first == second
    assert first.render() == second.render()


def test_supports_explicit_rendering_options() -> None:
    result = ImagePromptGenerator().generate(
        brief(),
        deliverable(),
        storyboard(),
        aspect_ratio=AspectRatio.LANDSCAPE,
        visual_style=VisualStyle.DOCUMENTARY,
    )

    assert result.prompts[0].aspect_ratio is AspectRatio.LANDSCAPE
    assert result.prompts[0].visual_style is VisualStyle.DOCUMENTARY
    assert "aspect ratio: 16:9" in result.render()


def test_rejects_non_image_prompt_deliverable() -> None:
    with pytest.raises(ImagePromptError, match="deliverable must be an image prompt"):
        ImagePromptGenerator().generate(
            brief(),
            deliverable(DeliverableType.CAPTION),
            storyboard(),
        )


def test_rejects_campaign_mismatch() -> None:
    with pytest.raises(ImagePromptError, match="must share a campaign"):
        ImagePromptGenerator().generate(
            brief(),
            deliverable(),
            storyboard("another-campaign"),
        )


def test_does_not_mutate_inputs_and_returns_immutable_models() -> None:
    source_brief = brief()
    source_deliverable = deliverable()
    source_storyboard = storyboard()
    original_scenes = source_storyboard.scenes

    result = ImagePromptGenerator().generate(
        source_brief,
        source_deliverable,
        source_storyboard,
    )

    assert source_storyboard.scenes == original_scenes
    with pytest.raises(FrozenInstanceError):
        result.prompts[0].subject = "Changed"
