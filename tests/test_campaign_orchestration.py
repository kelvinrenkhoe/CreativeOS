import pytest

from services.campaign_orchestration import (
    CampaignOrchestrationService,
    WorkflowEvidence,
)
from services.campaign_planner import CampaignIntent, CampaignPhaseDirection, CampaignPlan
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


def prepared():
    return CampaignOrchestrationService().prepare(
        "no-way-back-launch",
        context(),
        campaign(),
    )


def evidence(kind: str) -> WorkflowEvidence:
    return WorkflowEvidence(
        kind=kind,
        reference_id=f"{kind}-123",
        recorded_by="Kelvin",
    )


def test_prepares_one_coordinated_campaign_package() -> None:
    run = prepared()

    assert run.stage == "planned"
    assert run.plan.work_id == "no-way-back"
    assert run.cinematic_treatment.work_id == run.work_id
    assert run.video_prompt.work_id == run.work_id
    assert run.image_plan.work_id == run.work_id
    assert run.requires_action == "Begin production"


def test_advances_through_approval_gated_lifecycle() -> None:
    service = CampaignOrchestrationService()
    run = service.advance(prepared(), "in-production")
    run = service.advance(run, "ready", evidence=evidence("approved-assets"))
    run = service.advance(run, "published", evidence=evidence("publication-receipt"))
    run = service.advance(run, "measured", evidence=evidence("campaign-measurement"))
    run = service.advance(run, "completed")

    assert run.stage == "completed"
    assert tuple(item.kind for item in run.evidence) == (
        "approved-assets",
        "publication-receipt",
        "campaign-measurement",
    )
    assert run.requires_action == "No further action"


def test_rejects_skipped_stage() -> None:
    with pytest.raises(ValueError, match="must advance"):
        CampaignOrchestrationService().advance(prepared(), "ready")


def test_requires_exact_evidence_for_gated_stage() -> None:
    service = CampaignOrchestrationService()
    run = service.advance(prepared(), "in-production")

    with pytest.raises(PermissionError, match="approved-assets"):
        service.advance(run, "ready")

    with pytest.raises(PermissionError, match="approved-assets"):
        service.advance(run, "ready", evidence=evidence("publication-receipt"))


def test_rejects_evidence_when_transition_has_no_gate() -> None:
    with pytest.raises(ValueError, match="does not accept evidence"):
        CampaignOrchestrationService().advance(
            prepared(),
            "in-production",
            evidence=evidence("approved-assets"),
        )


def test_completed_campaign_cannot_advance() -> None:
    service = CampaignOrchestrationService()
    run = service.advance(prepared(), "in-production")
    run = service.advance(run, "ready", evidence=evidence("approved-assets"))
    run = service.advance(run, "published", evidence=evidence("publication-receipt"))
    run = service.advance(run, "measured", evidence=evidence("campaign-measurement"))
    run = service.advance(run, "completed")

    with pytest.raises(ValueError, match="cannot advance"):
        service.advance(run, "completed")


@pytest.mark.parametrize("value", ["", "unknown"])
def test_rejects_invalid_target_stage(value: str) -> None:
    with pytest.raises(ValueError, match="stage"):
        CampaignOrchestrationService().advance(prepared(), value)
