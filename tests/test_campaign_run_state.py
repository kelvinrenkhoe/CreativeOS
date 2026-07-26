import json
from dataclasses import replace

import pytest

from services.campaign_orchestration import (
    CampaignOrchestrationService,
    WorkflowEvidence,
)
from services.campaign_planner import CampaignIntent, CampaignPhaseDirection, CampaignPlan
from services.campaign_run_state import (
    CampaignRunCorruptedError,
    CampaignRunNotFoundError,
    CampaignRunValidationError,
    CampaignRunVersionError,
    JsonCampaignRunStore,
)
from story.context import StoryContext
from story.models import Character, CreativeWork, Location, Symbol, Theme


def prepared():
    context = StoryContext(
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
    plan = CampaignPlan(
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
    return CampaignOrchestrationService().prepare("no-way-back-launch", context, plan)


def ready_run():
    service = CampaignOrchestrationService()
    run = service.advance(prepared(), "in-production")
    return service.advance(
        run,
        "ready",
        evidence=WorkflowEvidence(
            kind="approved-assets",
            reference_id="asset-approval-123",
            recorded_by="Kelvin",
        ),
    )


def test_round_trips_complete_run_and_evidence(tmp_path) -> None:
    store = JsonCampaignRunStore(tmp_path)
    expected = ready_run()

    store.save(expected)
    restored = store.load(expected.campaign_id)

    assert restored == expected
    assert restored.stage == "ready"
    assert restored.evidence[0].recorded_by == "Kelvin"
    assert restored.requires_action == "Record publication-receipt evidence"


def test_replaces_existing_snapshot_with_latest_valid_state(tmp_path) -> None:
    store = JsonCampaignRunStore(tmp_path)
    initial = prepared()
    advanced = CampaignOrchestrationService().advance(initial, "in-production")

    store.save(initial)
    store.save(advanced)

    assert store.load(initial.campaign_id) == advanced
    assert not tuple(tmp_path.glob("*.tmp"))


def test_missing_run_has_specific_error(tmp_path) -> None:
    with pytest.raises(CampaignRunNotFoundError, match="missing"):
        JsonCampaignRunStore(tmp_path).load("missing")


@pytest.mark.parametrize("campaign_id", ["", "../escape", "nested/run"])
def test_rejects_unsafe_campaign_id(tmp_path, campaign_id: str) -> None:
    store = JsonCampaignRunStore(tmp_path)

    with pytest.raises(CampaignRunValidationError, match="safe file name"):
        store.load(campaign_id)


def test_rejects_unknown_snapshot_version(tmp_path) -> None:
    store = JsonCampaignRunStore(tmp_path)
    store.save(prepared())
    path = tmp_path / "no-way-back-launch.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = "999"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CampaignRunVersionError, match="999"):
        store.load("no-way-back-launch")


def test_rejects_corrupt_snapshot(tmp_path) -> None:
    (tmp_path / "no-way-back-launch.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(CampaignRunCorruptedError, match="corrupt"):
        JsonCampaignRunStore(tmp_path).load("no-way-back-launch")


def test_rejects_snapshot_with_mismatched_campaign_id(tmp_path) -> None:
    store = JsonCampaignRunStore(tmp_path)
    store.save(prepared())
    path = tmp_path / "no-way-back-launch.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["campaign_run"]["campaign_id"] = "another-campaign"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CampaignRunValidationError, match="Campaign ID mismatch"):
        store.load("no-way-back-launch")


def test_rejects_evidence_inconsistent_with_stage(tmp_path) -> None:
    store = JsonCampaignRunStore(tmp_path)
    invalid = replace(prepared(), evidence=ready_run().evidence)

    with pytest.raises(CampaignRunValidationError, match="does not match stage"):
        store.save(invalid)
