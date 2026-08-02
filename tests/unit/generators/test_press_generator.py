"""Tests for deterministic press and media package generation."""

import pytest

from generators.press import PressGenerator
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType
from models.media import MediaError
from models.press import PressAssetType


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
        story_context="A night-shift worker meets the sunrise.",
        memory="No prior media package.",
        completed_item_ids=(),
        ready_item_ids=("press-story",),
        blocked_items=(),
        next_item_id="press-story",
        next_reason="Ready.",
        recovery=None,
    )


def deliverable(**overrides) -> CreativeDeliverable:
    values = {
        "deliverable_id": "no-lose-guard-week-3-press-article",
        "deliverable_type": DeliverableType.PRESS_ARTICLE,
        "campaign_week": 3,
        "objective": "Build anticipation and drive streams.",
        "audience": "Afrobeats listeners who value perseverance.",
        "tone": "Hopeful, cinematic, and authentic.",
        "platforms": ("instagram", "tiktok"),
        "source_item_id": "press-story",
    }
    values.update(overrides)
    return CreativeDeliverable(**values)


def test_generates_stable_complete_media_package() -> None:
    generator = PressGenerator()

    first = generator.generate(brief(), deliverable())
    second = generator.generate(brief(), deliverable())

    assert first == second
    assert len(first.assets) == 10
    assert tuple(asset.asset_type for asset in first.assets) == tuple(PressAssetType)
    assert first.context.call_to_action.endswith("instagram, tiktok.")


def test_render_contains_campaign_and_media_sections() -> None:
    rendered = PressGenerator().generate(brief(), deliverable()).render()

    assert "# Media Package: No Lose Guard" in rendered
    assert "## Kelvin Rankie introduces No Lose Guard" in rendered
    assert "## Playlist pitch: No Lose Guard" in rendered
    assert "## Interview opportunity with Kelvin Rankie" in rendered


def test_rejects_non_press_deliverable() -> None:
    with pytest.raises(MediaError, match="must be a press article"):
        PressGenerator().generate(
            brief(),
            deliverable(deliverable_type=DeliverableType.CAPTION),
        )


def test_rejects_deliverable_from_another_campaign() -> None:
    with pytest.raises(MediaError, match="another campaign"):
        PressGenerator().generate(
            brief(),
            deliverable(deliverable_id="another-campaign-week-3-press-article"),
        )


def test_generation_does_not_mutate_inputs() -> None:
    source_brief = brief()
    source_deliverable = deliverable()

    PressGenerator().generate(source_brief, source_deliverable)

    assert source_brief.next_item_id == "press-story"
    assert source_deliverable.source_item_id == "press-story"
