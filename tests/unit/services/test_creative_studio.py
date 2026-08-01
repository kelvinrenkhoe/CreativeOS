"""Tests for deterministic Creative Studio planning."""

import pytest

from models.creative_brief import CreativeBrief
from models.creative_studio import CreativeStudioError, DeliverableType, StudioRequest
from services.creative_studio import CreativeStudioService


def brief(campaign_id: str = "no-lose-guard") -> CreativeBrief:
    return CreativeBrief(
        campaign_id=campaign_id,
        campaign_name="No Lose Guard",
        artist="Kelvin Rankie",
        objective="Build anticipation and drive streams.",
        audience="Afrobeats listeners who value perseverance.",
        tone="Hopeful, cinematic, and authentic.",
        platforms=("instagram", "tiktok"),
        knowledge="Song knowledge.",
        story_context="Night-shift worker reaches sunrise.",
        memory="No campaign assets have been generated yet.",
        completed_item_ids=("announcement",),
        ready_item_ids=("lyric-video",),
        blocked_items=(),
        next_item_id="lyric-video",
        next_reason="Earliest timeline item with all prerequisites completed.",
        recovery=None,
    )


def request(**overrides) -> StudioRequest:
    values = {
        "campaign_id": "no-lose-guard",
        "campaign_week": 3,
        "deliverable_types": (
            DeliverableType.STORYBOARD,
            DeliverableType.VIDEO_PROMPT,
            DeliverableType.CAPTION,
            DeliverableType.THUMBNAIL,
            DeliverableType.VOICEOVER,
        ),
    }
    values.update(overrides)
    return StudioRequest(**values)


def test_builds_ordered_weekly_package() -> None:
    output = CreativeStudioService().build(brief(), request())

    assert output.campaign_name == "No Lose Guard"
    assert output.campaign_week == 3
    assert tuple(item.deliverable_type for item in output.deliverables) == (
        DeliverableType.STORYBOARD,
        DeliverableType.VIDEO_PROMPT,
        DeliverableType.CAPTION,
        DeliverableType.THUMBNAIL,
        DeliverableType.VOICEOVER,
    )
    assert all(item.source_item_id == "lyric-video" for item in output.deliverables)


def test_output_is_deterministic() -> None:
    service = CreativeStudioService()

    first = service.build(brief(), request())
    second = service.build(brief(), request())

    assert first == second
    assert first.render() == second.render()


def test_render_contains_stable_deliverable_ids() -> None:
    rendered = CreativeStudioService().build(brief(), request()).render()

    assert "# Creative Studio: No Lose Guard" in rendered
    assert "no-lose-guard-week-3-storyboard" in rendered
    assert "no-lose-guard-week-3-video_prompt" in rendered


def test_rejects_campaign_mismatch() -> None:
    with pytest.raises(CreativeStudioError, match="another campaign"):
        CreativeStudioService().build(brief("another-campaign"), request())


def test_request_rejects_invalid_week() -> None:
    with pytest.raises(CreativeStudioError, match="at least 1"):
        request(campaign_week=0)


def test_request_rejects_duplicate_deliverables() -> None:
    with pytest.raises(CreativeStudioError, match="must be unique"):
        request(
            deliverable_types=(
                DeliverableType.CAPTION,
                DeliverableType.CAPTION,
            )
        )


def test_request_rejects_empty_deliverables() -> None:
    with pytest.raises(CreativeStudioError, match="must not be empty"):
        request(deliverable_types=())


def test_build_does_not_mutate_inputs() -> None:
    source_brief = brief()
    source_request = request()

    CreativeStudioService().build(source_brief, source_request)

    assert source_brief == brief()
    assert source_request == request()
