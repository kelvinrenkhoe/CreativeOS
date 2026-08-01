"""Tests for deterministic storyboard generation."""

import pytest

from generators.storyboard import StoryboardGenerator
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.storyboard import StoryboardError


def brief() -> CreativeBrief:
    return CreativeBrief(
        campaign_id="no-lose-guard",
        campaign_name="No Lose Guard",
        artist="Kelvin Rankie",
        objective="Build anticipation and drive streams.",
        audience="Afrobeats listeners who value perseverance.",
        tone="Hopeful, cinematic, and authentic.",
        platforms=("instagram", "tiktok"),
        knowledge="Song context.",
        story_context="Night-shift worker meets sunrise.",
        memory="No prior storyboard.",
        completed_item_ids=(),
        ready_item_ids=("lyric-video",),
        blocked_items=(),
        next_item_id="lyric-video",
        next_reason="Ready.",
        recovery=None,
    )


def deliverable(**overrides) -> CreativeDeliverable:
    values = {
        "deliverable_id": "no-lose-guard-week-3-storyboard",
        "deliverable_type": DeliverableType.STORYBOARD,
        "campaign_week": 3,
        "objective": "Build anticipation and drive streams.",
        "audience": "Afrobeats listeners who value perseverance.",
        "tone": "Hopeful, cinematic, and authentic.",
        "platforms": ("instagram", "tiktok"),
        "source_item_id": "lyric-video",
    }
    values.update(overrides)
    return CreativeDeliverable(**values)


def test_generates_stable_storyboard() -> None:
    generator = StoryboardGenerator()

    first = generator.generate(brief(), deliverable())
    second = generator.generate(brief(), deliverable())

    assert first == second
    assert first.total_duration_seconds == 17
    assert tuple(scene.scene_number for scene in first.scenes) == (1, 2, 3, 4)
    assert first.call_to_action.endswith("instagram, tiktok.")
    assert "# Storyboard: No Lose Guard — Week 3" in first.render()


def test_rejects_non_storyboard_deliverable() -> None:
    with pytest.raises(StoryboardError, match="must be a storyboard"):
        StoryboardGenerator().generate(
            brief(),
            deliverable(deliverable_type=DeliverableType.CAPTION),
        )


def test_rejects_deliverable_from_another_campaign() -> None:
    with pytest.raises(StoryboardError, match="another campaign"):
        StoryboardGenerator().generate(
            brief(),
            deliverable(deliverable_id="another-campaign-week-3-storyboard"),
        )


def test_generation_does_not_mutate_inputs() -> None:
    source_brief = brief()
    source_deliverable = deliverable()

    StoryboardGenerator().generate(source_brief, source_deliverable)

    assert source_brief.next_item_id == "lyric-video"
    assert source_deliverable.source_item_id == "lyric-video"
