import pytest

from services.cinematic_planner import (
    CinematicScene,
    CinematicTreatment,
    ShotDirection,
)
from services.video_prompt import VideoPromptService


def treatment() -> CinematicTreatment:
    return CinematicTreatment(
        work_id="no-way-back",
        work_name="No Way Back",
        concept="Cinematic, honest, and hopeful visual storytelling.",
        audience="Afrobeats listeners",
        platforms=("instagram", "tiktok"),
        visual_motifs=("Passport",),
        scenes=(
            CinematicScene(
                number=1,
                phase_id="departure",
                title="The Departure",
                narrative_purpose="Reveal the decision to leave.",
                setting="Family home",
                subjects=("Kelvin",),
                motifs=("Passport",),
                mood="Reflective",
                shots=(
                    ShotDirection(
                        number=1,
                        framing="Wide establishing shot",
                        movement="Slow push",
                        description="Kelvin prepares to leave the family home.",
                    ),
                    ShotDirection(
                        number=2,
                        framing="Close detail",
                        movement="Locked frame",
                        description="End on the passport in Kelvin's hand.",
                    ),
                ),
            ),
        ),
    )


def test_builds_provider_neutral_prompt_package() -> None:
    prompt = VideoPromptService().build(treatment())

    assert prompt.work_id == "no-way-back"
    assert prompt.duration_seconds == 10
    assert prompt.platforms == ("instagram", "tiktok")
    assert prompt.scenes[0].duration_seconds == 10

    shot = prompt.scenes[0].shots[0]
    assert shot.setting == "Family home"
    assert shot.subjects == ("Kelvin",)
    assert shot.motifs == ("Passport",)
    assert shot.duration_seconds == 5
    assert "Preserve the appearance of Kelvin" in shot.continuity


def test_supports_custom_shot_duration() -> None:
    prompt = VideoPromptService().build(treatment(), seconds_per_shot=8)

    assert prompt.duration_seconds == 16
    assert tuple(shot.duration_seconds for shot in prompt.scenes[0].shots) == (8, 8)


def test_renders_deterministic_markdown() -> None:
    rendered = VideoPromptService().build(treatment()).render()

    assert "# Video Prompt: No Way Back" in rendered
    assert "**Duration:** 10 seconds" in rendered
    assert "1. **5s:** Wide establishing shot in Family home." in rendered
    assert "Use a reflective mood and feature Passport." in rendered


def test_finds_scene_by_campaign_phase() -> None:
    prompt = VideoPromptService().build(treatment())

    assert prompt.scene_for_phase("departure").title == "The Departure"
    with pytest.raises(KeyError, match="missing"):
        prompt.scene_for_phase("missing")


def test_rejects_invalid_shot_duration() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        VideoPromptService().build(treatment(), seconds_per_shot=0)


def test_rejects_treatment_without_scenes() -> None:
    empty = CinematicTreatment(
        work_id="no-way-back",
        work_name="No Way Back",
        concept="A concept",
        audience="An audience",
        platforms=("youtube",),
        visual_motifs=(),
        scenes=(),
    )

    with pytest.raises(ValueError, match="at least one scene"):
        VideoPromptService().build(empty)


def test_rejects_scene_without_shots() -> None:
    source = treatment()
    empty_scene = CinematicScene(
        number=1,
        phase_id="departure",
        title="The Departure",
        narrative_purpose="Reveal the decision to leave.",
        setting="Family home",
        subjects=("Kelvin",),
        motifs=("Passport",),
        mood="Reflective",
        shots=(),
    )
    invalid = CinematicTreatment(
        work_id=source.work_id,
        work_name=source.work_name,
        concept=source.concept,
        audience=source.audience,
        platforms=source.platforms,
        visual_motifs=source.visual_motifs,
        scenes=(empty_scene,),
    )

    with pytest.raises(ValueError, match="departure"):
        VideoPromptService().build(invalid)
