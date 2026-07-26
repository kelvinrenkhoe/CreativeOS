import pytest

from services.campaign_planner import CampaignPlannerService
from story import (
    CreativeWork,
    NarrativeTimelineService,
    StoryArc,
    StoryBeat,
    StoryContext,
    WorkKind,
)


def build_context(work_id: str = "no-way-back") -> StoryContext:
    return StoryContext(
        universe_id="kelvin-rankie-universe",
        universe_name="Kelvin Rankie Universe",
        work=CreativeWork(id=work_id, name="No Way Back", kind=WorkKind.SONG),
        themes=(),
        characters=(),
        locations=(),
        symbols=(),
        arcs=(
            StoryArc(
                id="journey",
                name="Journey",
                beats=(
                    StoryBeat(id="pressure", summary="Establish the pressure to leave."),
                    StoryBeat(id="resolve", summary="Reveal resilience and hope."),
                ),
            ),
        ),
        relationships=(),
        knowledge="",
    )


def build_plan():
    context = build_context()
    timeline = NarrativeTimelineService().build(context, weeks=4)
    return CampaignPlannerService().build(
        context,
        timeline,
        objective="Grow discovery and meaningful streams",
        audience="Afrobeats listeners who value migration stories",
        tone="Cinematic, honest, and hopeful",
        platforms=("Instagram", "TikTok", "instagram"),
    )


def test_builds_direction_for_every_timeline_phase() -> None:
    plan = build_plan()

    assert plan.work_id == "no-way-back"
    assert plan.total_weeks == 4
    assert tuple(phase.phase_id for phase in plan.phases) == ("pressure", "resolve")
    assert plan.phases[0].narrative_objective == "Establish the pressure to leave."
    assert plan.phases[0].campaign_objective == "Grow discovery and meaningful streams"


def test_normalizes_and_deduplicates_platforms() -> None:
    plan = build_plan()

    assert plan.intent.platforms == ("instagram", "tiktok")
    assert all(phase.platforms == plan.intent.platforms for phase in plan.phases)


def test_resolves_direction_for_campaign_week() -> None:
    plan = build_plan()

    assert plan.direction_for_week(1).phase_id == "pressure"
    assert plan.direction_for_week(4).phase_id == "resolve"

    with pytest.raises(ValueError, match="week must be between 1 and 4"):
        plan.direction_for_week(5)


def test_rejects_timeline_for_a_different_work() -> None:
    context = build_context()
    other_context = build_context("different-work")
    timeline = NarrativeTimelineService().build(other_context, weeks=4)

    with pytest.raises(ValueError, match="does not match context work"):
        CampaignPlannerService().build(
            context,
            timeline,
            objective="Grow streams",
            audience="Afrobeats listeners",
            tone="Hopeful",
            platforms=("instagram",),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("objective", " ", "objective must not be empty"),
        ("audience", "", "audience must not be empty"),
        ("tone", "\t", "tone must not be empty"),
    ],
)
def test_rejects_empty_campaign_intent(field: str, value: str, message: str) -> None:
    context = build_context()
    timeline = NarrativeTimelineService().build(context, weeks=4)
    values = {
        "objective": "Grow streams",
        "audience": "Afrobeats listeners",
        "tone": "Hopeful",
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        CampaignPlannerService().build(
            context,
            timeline,
            platforms=("instagram",),
            **values,
        )


def test_rejects_empty_platforms() -> None:
    context = build_context()
    timeline = NarrativeTimelineService().build(context, weeks=4)

    with pytest.raises(ValueError, match="platforms must not be empty"):
        CampaignPlannerService().build(
            context,
            timeline,
            objective="Grow streams",
            audience="Afrobeats listeners",
            tone="Hopeful",
            platforms=(),
        )


def test_renders_deterministic_markdown() -> None:
    rendered = build_plan().render()

    assert rendered.startswith("# Campaign Plan: No Way Back")
    assert "**Objective:** Grow discovery and meaningful streams" in rendered
    assert "**Platforms:** instagram, tiktok" in rendered
    assert "## Phase 1: Pressure" in rendered
    assert "**Timing:** Weeks 1-2" in rendered
    assert "**Narrative objective:** Establish the pressure to leave." in rendered
