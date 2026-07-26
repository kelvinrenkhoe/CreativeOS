import pytest

from services.campaign_planner import (
    CampaignIntent,
    CampaignPhaseDirection,
    CampaignPlan,
)
from services.image_planner import ImagePlannerService
from story.context import StoryContext
from story.models import Character, CreativeWork, Location, Symbol, Theme


def context() -> StoryContext:
    return StoryContext(
        universe_id="kelvin-rankie",
        universe_name="Kelvin Rankie Universe",
        work=CreativeWork(id="no-way-back", name="No Way Back", kind="song"),
        themes=(Theme(id="migration", name="Migration"),),
        characters=(Character(id="kelvin", name="Kelvin"),),
        locations=(Location(id="family-home", name="Family home"),),
        symbols=(Symbol(id="passport", name="Passport"),),
        arcs=(),
        relationships=(),
        knowledge="",
    )


def campaign() -> CampaignPlan:
    return CampaignPlan(
        work_id="no-way-back",
        work_name="No Way Back",
        total_weeks=2,
        intent=CampaignIntent(
            objective="Grow meaningful discovery",
            audience="Afrobeats listeners",
            tone="Cinematic and hopeful",
            platforms=("instagram", "youtube"),
        ),
        phases=(
            CampaignPhaseDirection(
                phase_number=1,
                phase_id="departure",
                title="The Departure",
                start_week=1,
                end_week=2,
                narrative_objective="Reveal the decision to leave.",
                campaign_objective="Grow meaningful discovery",
                audience="Afrobeats listeners",
                tone="Reflective",
                platforms=("instagram", "youtube"),
            ),
        ),
    )


def test_builds_phase_aligned_image_concepts() -> None:
    plan = ImagePlannerService().build(context(), campaign())

    assert plan.work_id == "no-way-back"
    assert plan.platforms == ("instagram", "youtube")
    concept = plan.concept_for_phase("departure")
    assert concept.setting == "Family home"
    assert concept.subjects == ("Kelvin",)
    assert concept.motifs == ("Passport",)
    assert "approved appearance" in concept.identity_reference
    assert "identity drift" in concept.exclusions


def test_exposes_reusable_format_variants() -> None:
    concept = ImagePlannerService().build(context(), campaign()).concepts[0]

    assert tuple(item.name for item in concept.formats) == (
        "cover-art",
        "poster",
        "social-graphic",
        "thumbnail",
        "cinematic-still",
    )
    assert concept.format(" Poster ").aspect_ratio == "4:5"
    assert concept.format("cinematic-still").typography == "No text."


def test_renders_deterministic_markdown() -> None:
    rendered = ImagePlannerService().build(context(), campaign()).render()

    assert "# Image Plan: No Way Back" in rendered
    assert "**Identity:** Preserve the approved appearance" in rendered
    assert "**poster (4:5):**" in rendered
    assert "Typography: No text." in rendered


def test_falls_back_to_themes_when_symbols_are_missing() -> None:
    source = context()
    without_symbols = StoryContext(
        universe_id=source.universe_id,
        universe_name=source.universe_name,
        work=source.work,
        themes=source.themes,
        characters=source.characters,
        locations=source.locations,
        symbols=(),
        arcs=source.arcs,
        relationships=source.relationships,
        knowledge=source.knowledge,
    )

    concept = ImagePlannerService().build(without_symbols, campaign()).concepts[0]

    assert concept.motifs == ("Migration",)


def test_rejects_mismatched_story_context() -> None:
    source = context()
    other_context = StoryContext(
        universe_id=source.universe_id,
        universe_name=source.universe_name,
        work=CreativeWork(id="another-work", name="Another Work", kind="song"),
        themes=source.themes,
        characters=source.characters,
        locations=source.locations,
        symbols=source.symbols,
        arcs=source.arcs,
        relationships=source.relationships,
        knowledge=source.knowledge,
    )

    with pytest.raises(ValueError, match="does not match"):
        ImagePlannerService().build(other_context, campaign())


def test_rejects_campaign_without_phases() -> None:
    source = campaign()
    empty = CampaignPlan(
        work_id=source.work_id,
        work_name=source.work_name,
        total_weeks=source.total_weeks,
        intent=source.intent,
        phases=(),
    )

    with pytest.raises(ValueError, match="at least one phase"):
        ImagePlannerService().build(context(), empty)


def test_rejects_unknown_format() -> None:
    concept = ImagePlannerService().build(context(), campaign()).concepts[0]

    with pytest.raises(KeyError, match="landscape-banner"):
        concept.format("landscape-banner")
