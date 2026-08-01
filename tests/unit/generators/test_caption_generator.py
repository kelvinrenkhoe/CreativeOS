"""Tests for deterministic platform-aware caption generation."""

from dataclasses import FrozenInstanceError

import pytest

from generators.caption import CaptionGenerator
from models.caption import (
    CaptionError,
    CaptionHistory,
    CaptionPlatform,
    CaptionRequest,
    CaptionStructure,
)
from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeDeliverable, DeliverableType


def brief(campaign_id: str = "no-lose-guard") -> CreativeBrief:
    return CreativeBrief(
        campaign_id=campaign_id,
        campaign_name="No Lose Guard",
        artist="Kelvin Rankie",
        objective="Build anticipation.",
        audience="Afrobeats listeners.",
        tone="Hopeful and cinematic.",
        platforms=("instagram", "tiktok", "facebook"),
        knowledge="A song about perseverance.",
        story_context="A worker keeps moving toward sunrise.",
        memory="Previous campaign content is supplied explicitly.",
        completed_item_ids=(),
        ready_item_ids=("caption",),
        blocked_items=(),
        next_item_id="video-prompt",
        next_reason="Ready.",
        recovery=None,
    )


def deliverable(
    kind: DeliverableType = DeliverableType.CAPTION,
    campaign_id: str = "no-lose-guard",
) -> CreativeDeliverable:
    return CreativeDeliverable(
        deliverable_id=f"{campaign_id}-week-3-{kind.value}",
        deliverable_type=kind,
        campaign_week=3,
        objective="Build anticipation.",
        audience="Afrobeats listeners.",
        tone="Hopeful and cinematic.",
        platforms=("instagram", "tiktok", "facebook"),
        source_item_id="video-prompt",
    )


def request() -> CaptionRequest:
    return CaptionRequest(
        platforms=(
            CaptionPlatform.INSTAGRAM,
            CaptionPlatform.TIKTOK,
            CaptionPlatform.FACEBOOK,
            CaptionPlatform.X,
            CaptionPlatform.WHATSAPP,
        )
    )


def test_generates_one_variant_per_requested_platform() -> None:
    result = CaptionGenerator().generate(brief(), deliverable(), request())

    assert tuple(item.platform for item in result.variants) == request().platforms
    assert len({item.caption_id for item in result.variants}) == 5
    assert result.variants[-1].hashtags == ()
    assert "## instagram" in result.render()


def test_output_is_deterministic() -> None:
    generator = CaptionGenerator()

    first = generator.generate(brief(), deliverable(), request())
    second = generator.generate(brief(), deliverable(), request())

    assert first == second
    assert first.render() == second.render()


def test_avoids_explicitly_blocked_content_elements() -> None:
    history = CaptionHistory(
        hooks=("Some seasons test how firmly you can stand.",),
        calls_to_action=("Follow the journey and stay ready for the next chapter.",),
        emotional_angles=("quiet resilience",),
        hashtags=("#NoLoseGuard",),
        structures=(CaptionStructure.HOOK_STORY_CTA,),
    )
    source_request = CaptionRequest(
        platforms=(CaptionPlatform.INSTAGRAM,),
        history=history,
    )

    variant = CaptionGenerator().generate(brief(), deliverable(), source_request).variants[0]

    assert variant.hook not in history.hooks
    assert variant.call_to_action not in history.calls_to_action
    assert variant.emotional_angle not in history.emotional_angles
    assert variant.structure not in history.structures
    assert not set(variant.hashtags).intersection(history.hashtags)


def test_rejects_non_caption_deliverable() -> None:
    with pytest.raises(CaptionError, match="deliverable must be a caption"):
        CaptionGenerator().generate(
            brief(),
            deliverable(DeliverableType.VIDEO_PROMPT),
            request(),
        )


def test_rejects_campaign_mismatch() -> None:
    with pytest.raises(CaptionError, match="share a campaign"):
        CaptionGenerator().generate(
            brief(),
            deliverable(campaign_id="another-campaign"),
            request(),
        )


def test_request_rejects_duplicate_platforms() -> None:
    with pytest.raises(CaptionError, match="platforms must be unique"):
        CaptionRequest(
            platforms=(CaptionPlatform.INSTAGRAM, CaptionPlatform.INSTAGRAM),
        )


def test_models_are_immutable_and_inputs_are_not_mutated() -> None:
    source_brief = brief()
    source_deliverable = deliverable()
    source_request = request()
    original_platforms = source_request.platforms

    result = CaptionGenerator().generate(source_brief, source_deliverable, source_request)

    assert source_request.platforms == original_platforms
    with pytest.raises(FrozenInstanceError):
        result.variants[0].hook = "Changed"
