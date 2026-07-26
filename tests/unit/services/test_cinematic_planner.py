import pytest

from services.campaign_planner import CampaignPlannerService
from services.cinematic_planner import CinematicPlannerService
from story import (
    Character,
    CreativeWork,
    Location,
    NarrativeTimelineService,
    StoryArc,
    StoryBeat,
    StoryContext,
    Symbol,
    WorkKind,
)


def build_context(work_id: str = "no-way-back") -> StoryContext:
    return StoryContext(
        universe_id="kelvin-rankie-universe",
        universe_name="Kelvin Rankie Universe",
        work=CreativeWork(id=work_id, name="No Way Back", kind=WorkKind.SONG),
        themes=(),
        characters=(Character(id="kelvin", name="Kelvin"),),
        locations=(
            Location(id="lagos", name="Lagos"),
            Location(id="london", name="London"),
        ),
        symbols=(Symbol(id="passport", name="Passport"),),
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


def build_plan(context: StoryContext):
    timeline = NarrativeTimelineService().build(context, weeks=4)
    return CampaignPlannerService().build(
        context,
        timeline,
        objective="Grow discovery and meaningful streams",
        audience="Afrobeats listeners who value migration stories",
        tone="Cinematic, honest, and hopeful",
        platforms=("instagram", "tiktok"),
    )


def test_builds_one_grounded_scene_per_campaign_phase() -> None:
    context = build_context()
    treatment = CinematicPlannerService().build(context, build_plan(context))

    assert treatment.work_id == "no-way-back"
    assert treatment.visual_motifs == ("Passport",)
    assert tuple(scene.phase_id for scene in treatment.scenes) == ("pressure", "resolve")
    assert tuple(scene.setting for scene in treatment.scenes) == ("Lagos", "London")
    assert all(scene.subjects == ("Kelvin",) for scene in treatment.scenes)
    assert all(len(scene.shots) == 3 for scene in treatment.scenes)


def test_resolves_scene_for_phase() -> None:
    context = build_context()
    treatment = CinematicPlannerService().build(context, build_plan(context))

    assert treatment.scene_for_phase("resolve").title == "Resolve"

    with pytest.raises(KeyError, match="cinematic scene not found"):
        treatment.scene_for_phase("missing")


def test_uses_themes_when_story_has_no_symbols() -> None:
    context = build_context()
    context = StoryContext(
        universe_id=context.universe_id,
        universe_name=context.universe_name,
        work=context.work,
        themes=(),
        characters=context.characters,
        locations=context.locations,
        symbols=(),
        arcs=context.arcs,
        relationships=context.relationships,
        knowledge=context.knowledge,
    )

    treatment = CinematicPlannerService().build(context, build_plan(context))

    assert treatment.visual_motifs == ()
    assert treatment.scenes[0].shots[-1].description == "End on a meaningful story detail."


def test_rejects_plan_for_a_different_work() -> None:
    context = build_context()
    other_context = build_context("different-work")

    with pytest.raises(ValueError, match="does not match context work"):
        CinematicPlannerService().build(context, build_plan(other_context))


def test_renders_deterministic_markdown() -> None:
    context = build_context()
    rendered = CinematicPlannerService().build(context, build_plan(context)).render()

    assert rendered.startswith("# Cinematic Treatment: No Way Back")
    assert "**Visual motifs:** Passport" in rendered
    assert "## Scene 1: Pressure" in rendered
    assert "**Setting:** Lagos" in rendered
    assert "1. **Wide establishing shot / Slow push:**" in rendered
