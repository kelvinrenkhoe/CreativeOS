"""Tests for deterministic scene-aligned voice-over generation."""

import pytest

from generators.storyboard import StoryboardGenerator
from generators.voiceover import VoiceoverGenerator
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.voiceover import NarrationPace, VoiceoverError, VoiceoverStyle


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
        memory="No prior voice-over.",
        completed_item_ids=(),
        ready_item_ids=("lyric-video",),
        blocked_items=(),
        next_item_id="lyric-video",
        next_reason="Ready.",
        recovery=None,
    )


def deliverable(kind: DeliverableType, suffix: str, week: int = 3) -> CreativeDeliverable:
    return CreativeDeliverable(
        deliverable_id=f"no-lose-guard-week-{week}-{suffix}",
        deliverable_type=kind,
        campaign_week=week,
        objective="Build anticipation and drive streams.",
        audience="Afrobeats listeners who value perseverance.",
        tone="Hopeful, cinematic, and authentic.",
        platforms=("instagram", "tiktok"),
        source_item_id="lyric-video",
    )


def storyboard():
    return StoryboardGenerator().generate(
        brief(),
        deliverable(DeliverableType.STORYBOARD, "storyboard"),
    )


def test_generates_stable_scene_aligned_script() -> None:
    generator = VoiceoverGenerator()
    voiceover = deliverable(DeliverableType.VOICEOVER, "voiceover")

    first = generator.generate(brief(), voiceover, storyboard())
    second = generator.generate(brief(), voiceover, storyboard())

    assert first == second
    assert len(first.segments) == 4
    assert first.total_duration_seconds == 17
    assert tuple(segment.scene_number for segment in first.segments) == (1, 2, 3, 4)
    assert first.call_to_action.endswith("instagram, tiktok.")
    assert "# Voice-over: No Lose Guard — Week 3 Voice-over" in first.render()


def test_maps_storyboard_moods_to_delivery() -> None:
    result = VoiceoverGenerator().generate(
        brief(),
        deliverable(DeliverableType.VOICEOVER, "voiceover"),
        storyboard(),
    )

    assert result.segments[0].style is VoiceoverStyle.REFLECTIVE
    assert result.segments[0].pace is NarrationPace.SLOW
    assert result.segments[-1].style is VoiceoverStyle.CINEMATIC
    assert result.segments[-1].pace is NarrationPace.ENERGETIC


def test_rejects_non_voiceover_deliverable() -> None:
    with pytest.raises(VoiceoverError, match="must be a voiceover"):
        VoiceoverGenerator().generate(
            brief(),
            deliverable(DeliverableType.CAPTION, "caption"),
            storyboard(),
        )


def test_rejects_deliverable_from_another_campaign() -> None:
    wrong = CreativeDeliverable(
        deliverable_id="another-campaign-week-3-voiceover",
        deliverable_type=DeliverableType.VOICEOVER,
        campaign_week=3,
        objective="Build anticipation.",
        audience="Listeners.",
        tone="Hopeful.",
        platforms=("instagram",),
        source_item_id="lyric-video",
    )
    with pytest.raises(VoiceoverError, match="another campaign"):
        VoiceoverGenerator().generate(brief(), wrong, storyboard())


def test_rejects_cross_week_storyboard() -> None:
    with pytest.raises(VoiceoverError, match="campaign week"):
        VoiceoverGenerator().generate(
            brief(),
            deliverable(DeliverableType.VOICEOVER, "voiceover", week=4),
            storyboard(),
        )


def test_generation_does_not_mutate_inputs() -> None:
    source_brief = brief()
    source_deliverable = deliverable(DeliverableType.VOICEOVER, "voiceover")
    source_storyboard = storyboard()

    VoiceoverGenerator().generate(source_brief, source_deliverable, source_storyboard)

    assert source_brief.next_item_id == "lyric-video"
    assert source_deliverable.source_item_id == "lyric-video"
    assert source_storyboard.total_duration_seconds == 17
