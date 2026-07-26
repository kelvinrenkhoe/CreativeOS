import pytest

from services.campaign_planner import CampaignPlannerService
from services.daily_recommendation import DailyRecommendationService
from story import (
    CreativeWork,
    NarrativeTimelineService,
    StoryArc,
    StoryBeat,
    StoryContext,
    WorkKind,
)


def build_plan():
    context = StoryContext(
        universe_id="kelvin-rankie-universe",
        universe_name="Kelvin Rankie Universe",
        work=CreativeWork(id="no-way-back", name="No Way Back", kind=WorkKind.SONG),
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
    timeline = NarrativeTimelineService().build(context, weeks=4)
    return CampaignPlannerService().build(
        context,
        timeline,
        objective="Grow discovery and meaningful streams",
        audience="Afrobeats listeners who value migration stories",
        tone="Cinematic, honest, and hopeful",
        platforms=("Instagram", "TikTok"),
    )


def test_recommends_the_active_campaign_direction() -> None:
    recommendation = DailyRecommendationService().recommend(build_plan(), week=3)

    assert recommendation.work_id == "no-way-back"
    assert recommendation.week == 3
    assert recommendation.phase_id == "resolve"
    assert recommendation.phase_title == "Resolve"
    assert recommendation.narrative_focus == "Reveal resilience and hope."
    assert recommendation.platforms == ("instagram", "tiktok")


def test_rejects_a_week_outside_the_campaign() -> None:
    with pytest.raises(ValueError, match="week must be between 1 and 4"):
        DailyRecommendationService().recommend(build_plan(), week=5)


def test_renders_deterministic_markdown() -> None:
    rendered = DailyRecommendationService().recommend(build_plan(), week=1).render()

    assert rendered.startswith("# Next Recommendation: No Way Back")
    assert "**Campaign week:** 1 of 4" in rendered
    assert "**Active phase:** 1 — Pressure" in rendered
    assert "**Narrative focus:** Establish the pressure to leave." in rendered
    assert "**Platforms:** instagram, tiktok" in rendered
