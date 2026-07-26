import pytest

from story import (
    CreativeWork,
    NarrativeTimelineService,
    StoryArc,
    StoryBeat,
    StoryContext,
    WorkKind,
)


def build_context(*arcs: StoryArc) -> StoryContext:
    return StoryContext(
        universe_id="kelvin-rankie-universe",
        universe_name="Kelvin Rankie Universe",
        work=CreativeWork(
            id="no-way-back",
            name="No Way Back",
            kind=WorkKind.SONG,
        ),
        themes=(),
        characters=(),
        locations=(),
        symbols=(),
        arcs=arcs,
        relationships=(),
        knowledge="",
    )


def build_arc() -> StoryArc:
    return StoryArc(
        id="journey-home",
        name="Journey Home",
        beats=(
            StoryBeat(id="pressure", summary="Establish the pressure to leave."),
            StoryBeat(id="crossing", summary="Enter the uncertain journey."),
            StoryBeat(id="resolve", summary="Reveal resilience and hope."),
        ),
    )


def test_distributes_campaign_weeks_across_ordered_story_beats() -> None:
    timeline = NarrativeTimelineService().build(build_context(build_arc()), weeks=6)

    assert timeline.work_id == "no-way-back"
    assert timeline.arc_id == "journey-home"
    assert tuple(phase.id for phase in timeline.phases) == (
        "pressure",
        "crossing",
        "resolve",
    )
    assert tuple(
        (phase.start_week, phase.end_week, phase.duration_weeks)
        for phase in timeline.phases
    ) == ((1, 2, 2), (3, 4, 2), (5, 6, 2))


def test_assigns_remainder_weeks_to_earliest_phases() -> None:
    timeline = NarrativeTimelineService().build(build_context(build_arc()), weeks=5)

    assert tuple(
        (phase.start_week, phase.end_week) for phase in timeline.phases
    ) == ((1, 2), (3, 4), (5, 5))


def test_resolves_the_phase_for_a_campaign_week() -> None:
    timeline = NarrativeTimelineService().build(build_context(build_arc()), weeks=6)

    assert timeline.phase_for_week(4).id == "crossing"

    with pytest.raises(ValueError, match="week must be between 1 and 6"):
        timeline.phase_for_week(7)


def test_requires_arc_selection_when_context_has_multiple_arcs() -> None:
    second_arc = StoryArc(
        id="alternate",
        name="Alternate",
        beats=(StoryBeat(id="arrival", summary="Arrive."),),
    )
    context = build_context(build_arc(), second_arc)

    with pytest.raises(ValueError, match="arc_id is required"):
        NarrativeTimelineService().build(context, weeks=3)

    timeline = NarrativeTimelineService().build(
        context,
        weeks=3,
        arc_id="alternate",
    )
    assert timeline.arc_id == "alternate"


def test_rejects_campaigns_shorter_than_the_story_arc() -> None:
    with pytest.raises(ValueError, match=r"campaign weeks \(2\) must cover all story beats \(3\)"):
        NarrativeTimelineService().build(build_context(build_arc()), weeks=2)


def test_rejects_missing_or_empty_arcs() -> None:
    service = NarrativeTimelineService()

    with pytest.raises(ValueError, match="story context has no arcs"):
        service.build(build_context(), weeks=4)

    empty_arc = StoryArc(id="empty", name="Empty")
    with pytest.raises(ValueError, match="story arc has no beats: empty"):
        service.build(build_context(empty_arc), weeks=4)


def test_renders_deterministic_markdown() -> None:
    rendered = NarrativeTimelineService().build(
        build_context(build_arc()),
        weeks=6,
    ).render()

    assert rendered.startswith("# Narrative Timeline: No Way Back")
    assert "**Story arc:** Journey Home" in rendered
    assert "## Phase 1: Pressure" in rendered
    assert "**Timing:** Weeks 1-2" in rendered
    assert "**Objective:** Establish the pressure to leave." in rendered
