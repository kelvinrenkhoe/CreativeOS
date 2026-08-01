"""Tests for deterministic creative brief assembly."""

import pytest

from models.campaign_recovery import RecoveryAction, RecoveryPlan, RecoveryReason
from models.creative_brief import CreativeBriefError, CreativeBriefRequest
from services.campaign_execution import CampaignExecutionState, ExecutionBlockedItem
from services.campaign_memory import CampaignMemory
from services.creative_brief import CreativeBriefService


def request(**overrides) -> CreativeBriefRequest:
    values = {
        "campaign_id": "no-lose-guard",
        "campaign_name": "No Lose Guard",
        "artist": "Kelvin Rankie",
        "objective": "Build anticipation and drive streams.",
        "audience": "Afrobeats listeners who value perseverance.",
        "tone": "Hopeful, cinematic, and authentic.",
        "platforms": ("instagram", "tiktok"),
        "knowledge": "No Lose Guard is a song about refusing to give up.",
        "story_context": "A night-shift worker walks into sunrise after a difficult week.",
    }
    values.update(overrides)
    return CreativeBriefRequest(**values)


def execution(campaign_id: str = "no-lose-guard") -> CampaignExecutionState:
    return CampaignExecutionState(
        campaign_id=campaign_id,
        ordered_item_ids=("announcement", "lyric-video", "release-day"),
        completed_item_ids=("announcement",),
        ready_item_ids=("lyric-video",),
        blocked_items=(ExecutionBlockedItem("release-day", ("lyric-video",)),),
        next_item_id="lyric-video",
        next_reason="Earliest timeline item with all prerequisites completed.",
    )


def recovery(campaign_id: str = "no-lose-guard") -> RecoveryPlan:
    return RecoveryPlan(
        campaign_id=campaign_id,
        original_item_ids=("announcement", "lyric-video", "release-day"),
        recovered_item_ids=("announcement", "release-day", "lyric-video"),
        completed_item_ids=("announcement",),
        fixed_milestone_ids=("release-day",),
        actions=(
            RecoveryAction(
                item_id="lyric-video",
                original_position=2,
                recovered_position=3,
                reason=RecoveryReason.MISSED_CONTENT,
            ),
        ),
    )


def test_builds_unified_creative_brief() -> None:
    memory = CampaignMemory()
    memory.add(
        relative_path="captions/instagram.md",
        purpose="Instagram launch caption",
        content="You have come too far to lose guard.",
    )

    brief = CreativeBriefService().build(request(), execution(), memory, recovery())

    assert brief.campaign_name == "No Lose Guard"
    assert brief.next_item_id == "lyric-video"
    assert brief.blocked_items[0].unmet_prerequisite_ids == ("lyric-video",)
    assert "Instagram launch caption" in brief.memory
    assert brief.recovery is not None
    assert brief.recovery.moved_item_ids == ("lyric-video",)


def test_render_is_deterministic_and_complete() -> None:
    brief = CreativeBriefService().build(request(), execution(), CampaignMemory(), recovery())

    first = brief.render()
    second = brief.render()

    assert first == second
    assert "# Creative Brief: No Lose Guard" in first
    assert "Next: lyric-video" in first
    assert "release-day: lyric-video" in first
    assert "Recovered order: announcement, release-day, lyric-video" in first


def test_uses_explicit_fallbacks_for_empty_optional_context() -> None:
    brief = CreativeBriefService().build(
        request(knowledge="", story_context=""),
        execution(),
        CampaignMemory(),
    )

    assert brief.knowledge == "No artist or song knowledge was supplied."
    assert brief.story_context == "No story context was supplied."
    assert brief.memory == "No campaign assets have been generated yet."
    assert brief.recovery is None
    assert "## Recovery\nNot supplied." in brief.render()


def test_rejects_execution_state_from_another_campaign() -> None:
    with pytest.raises(CreativeBriefError, match="execution state belongs"):
        CreativeBriefService().build(
            request(),
            execution("another-campaign"),
            CampaignMemory(),
        )


def test_rejects_recovery_plan_from_another_campaign() -> None:
    with pytest.raises(CreativeBriefError, match="recovery plan belongs"):
        CreativeBriefService().build(
            request(),
            execution(),
            CampaignMemory(),
            recovery("another-campaign"),
        )


@pytest.mark.parametrize(
    "field_name",
    ("campaign_id", "campaign_name", "artist", "objective", "audience", "tone"),
)
def test_request_rejects_blank_required_fields(field_name: str) -> None:
    with pytest.raises(CreativeBriefError, match=field_name):
        request(**{field_name: "  "})


def test_request_normalizes_and_validates_platforms() -> None:
    normalized = request(platforms=(" instagram ", "tiktok"))
    assert normalized.platforms == ("instagram", "tiktok")

    with pytest.raises(CreativeBriefError, match="platforms must be unique"):
        request(platforms=("instagram", "instagram"))


def test_build_does_not_mutate_memory() -> None:
    memory = CampaignMemory()
    original_entries = list(memory.entries)

    CreativeBriefService().build(request(), execution(), memory)

    assert memory.entries == original_entries
