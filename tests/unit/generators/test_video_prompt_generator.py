"""Tests for deterministic video prompt generation."""

from dataclasses import FrozenInstanceError

import pytest

from generators.image_prompt import ImagePromptGenerator
from generators.video_prompt import VideoPromptGenerator
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.storyboard import (
    CameraMovement,
    CameraShot,
    LightingStyle,
    SceneMood,
    SceneTransition,
    Storyboard,
    StoryboardScene,
)
from models.video_prompt import (
    ContinuityMode,
    MotionIntensity,
    Pacing,
    VideoPromptError,
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
        ready_item_ids=("video-prompt",),
        blocked_items=(),
        next_item_id="video-prompt",
        next_reason="Ready.",
        recovery=None,
    )


def deliverable(kind: DeliverableType = DeliverableType.VIDEO_PROMPT) -> CreativeDeliverable:
    return CreativeDeliverable(
        deliverable_id=f"no-lose-guard-week-3-{kind.value}",
        deliverable_type=kind,
        campaign_week=3,
        objective="Build anticipation.",
        audience="Afrobeats listeners.",
        tone="Hopeful and cinematic.",
        platforms=("instagram", "tiktok"),
        source_item_id="video-prompt",
    )


def image_deliverable() -> CreativeDeliverable:
    return deliverable(DeliverableType.IMAGE_PROMPT)


def storyboard(campaign_id: str = "no-lose-guard") -> Storyboard:
    scenes = (
        StoryboardScene(
            1,
            5,
            "Night-shift exit",
            ("Kelvin",),
            "Walks into the early morning air.",
            "Tired but focused.",
            CameraShot.WIDE,
            CameraMovement.TRACK,
            LightingStyle.GOLDEN_HOUR,
            SceneMood.REFLECTIVE,
            "Instrumental intro.",
            SceneTransition.CUT,
        ),
        StoryboardScene(
            2,
            5,
            "Quiet London street",
            ("Kelvin",),
            "Raises his head and keeps walking.",
            "Determined.",
            CameraShot.CLOSE_UP,
            CameraMovement.PUSH_IN,
            LightingStyle.NATURAL,
            SceneMood.HOPEFUL,
            "Hook begins.",
            SceneTransition.FADE,
        ),
    )
    return Storyboard(
        f"{campaign_id}-week-3-storyboard",
        campaign_id,
        "No Lose Guard",
        3,
        "Keep Moving",
        "Build anticipation.",
        "Afrobeats listeners.",
        "Hopeful and cinematic.",
        ("instagram", "tiktok"),
        "Pre-save No Lose Guard.",
        scenes,
    )


def image_prompts(source_brief: CreativeBrief, source_storyboard: Storyboard):
    return ImagePromptGenerator().generate(
        source_brief,
        image_deliverable(),
        source_storyboard,
    )


def test_generates_one_video_prompt_per_scene() -> None:
    source_brief = brief()
    source_storyboard = storyboard()
    result = VideoPromptGenerator().generate(
        source_brief,
        deliverable(),
        source_storyboard,
        image_prompts(source_brief, source_storyboard),
    )

    assert len(result.prompts) == 2
    assert result.total_duration_seconds == source_storyboard.total_duration_seconds
    assert result.prompts[0].visual_reference_prompt_id.endswith("scene-1")


def test_output_is_deterministic() -> None:
    source_brief = brief()
    source_storyboard = storyboard()
    images = image_prompts(source_brief, source_storyboard)
    generator = VideoPromptGenerator()

    first = generator.generate(source_brief, deliverable(), source_storyboard, images)
    second = generator.generate(source_brief, deliverable(), source_storyboard, images)

    assert first == second
    assert first.render() == second.render()


def test_supports_explicit_direction_options() -> None:
    source_brief = brief()
    source_storyboard = storyboard()
    result = VideoPromptGenerator().generate(
        source_brief,
        deliverable(),
        source_storyboard,
        image_prompts(source_brief, source_storyboard),
        pacing=Pacing.FAST,
        motion_intensity=MotionIntensity.DYNAMIC,
        continuity_mode=ContinuityMode.FLEXIBLE,
    )

    assert result.prompts[0].pacing is Pacing.FAST
    assert result.prompts[0].motion_intensity is MotionIntensity.DYNAMIC
    assert result.continuity_mode is ContinuityMode.FLEXIBLE


def test_rejects_non_video_deliverable() -> None:
    source_brief = brief()
    source_storyboard = storyboard()
    with pytest.raises(VideoPromptError, match="deliverable must be a video prompt"):
        VideoPromptGenerator().generate(
            source_brief,
            deliverable(DeliverableType.CAPTION),
            source_storyboard,
            image_prompts(source_brief, source_storyboard),
        )


def test_rejects_campaign_mismatch() -> None:
    source_brief = brief()
    source_storyboard = storyboard("another-campaign")
    with pytest.raises(VideoPromptError, match="share a campaign"):
        VideoPromptGenerator().generate(
            source_brief,
            deliverable(),
            source_storyboard,
            image_prompts(brief("another-campaign"), source_storyboard),
        )


def test_models_are_immutable() -> None:
    source_brief = brief()
    source_storyboard = storyboard()
    result = VideoPromptGenerator().generate(
        source_brief,
        deliverable(),
        source_storyboard,
        image_prompts(source_brief, source_storyboard),
    )

    with pytest.raises(FrozenInstanceError):
        result.prompts[0].subject_motion = "Changed"
