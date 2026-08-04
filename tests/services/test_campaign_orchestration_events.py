"""Tests for durable campaign orchestration event history."""

import json
from types import SimpleNamespace

import pytest

from services.campaign_orchestration_events import (
    JsonOrchestrationEventStore,
    OrchestrationEventStoreCorruptedError,
    OrchestrationEventStoreVersionError,
)


def event(kind="step-completed", *, campaign_id="campaign-1", step=1):
    return SimpleNamespace(
        kind=kind,
        step=step,
        campaign_id=campaign_id,
        stage="ready",
        action="queued",
        request_id="request-1",
        detail=None,
    )


def test_append_and_load_preserve_order_and_metadata(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)

    stored = store.append(
        campaign_id="campaign-1",
        run_id="run-1",
        policy="until-complete",
        events=(event("campaign-started", step=0), event()),
    )

    assert [item.sequence for item in stored] == [1, 2]
    assert [item.kind for item in store.load("campaign-1")] == [
        "campaign-started",
        "step-completed",
    ]
    assert all(item.run_id == "run-1" for item in stored)
    assert all(item.policy == "until-complete" for item in stored)


def test_multiple_runs_append_to_same_campaign_history(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)
    store.append(campaign_id="campaign-1", run_id="run-1", policy="once", events=(event(),))
    store.append(
        campaign_id="campaign-1",
        run_id="run-2",
        policy="until-blocked",
        events=(event("campaign-blocked", step=2),),
    )

    history = store.load("campaign-1")

    assert [item.run_id for item in history] == ["run-1", "run-2"]
    assert [item.sequence for item in history] == [1, 1]


def test_generator_input_is_persisted_and_validated(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)

    stored = store.append(
        campaign_id="campaign-1",
        run_id="run-1",
        policy="once",
        events=(item for item in (event(),)),
    )

    assert len(stored) == 1
    assert store.load("campaign-1") == stored


def test_duplicate_run_id_is_rejected(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)
    store.append(campaign_id="campaign-1", run_id="run-1", policy="once", events=(event(),))

    with pytest.raises(ValueError, match="orchestration run already exists"):
        store.append(
            campaign_id="campaign-1",
            run_id="run-1",
            policy="once",
            events=(event(),),
        )


def test_mismatched_campaign_event_is_rejected_without_writing(tmp_path) -> None:
    store = JsonOrchestrationEventStore(tmp_path)

    with pytest.raises(ValueError, match="event campaign IDs must match"):
        store.append(
            campaign_id="campaign-1",
            run_id="run-1",
            policy="once",
            events=(event(campaign_id="campaign-2"),),
        )

    assert store.load("campaign-1") == ()


def test_missing_history_returns_empty_tuple(tmp_path) -> None:
    assert JsonOrchestrationEventStore(tmp_path).load("missing") == ()


def test_corrupt_history_reports_structured_error(tmp_path) -> None:
    (tmp_path / "campaign-1.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(OrchestrationEventStoreCorruptedError, match="history is corrupt"):
        JsonOrchestrationEventStore(tmp_path).load("campaign-1")


def test_unsupported_version_is_rejected(tmp_path) -> None:
    (tmp_path / "campaign-1.json").write_text(
        json.dumps({"version": "99", "events": []}),
        encoding="utf-8",
    )

    with pytest.raises(OrchestrationEventStoreVersionError, match="version: 99"):
        JsonOrchestrationEventStore(tmp_path).load("campaign-1")


@pytest.mark.parametrize("campaign_id", ["", ".", "..", "bad/name", "bad\\name"])
def test_campaign_id_must_be_safe_file_name(tmp_path, campaign_id) -> None:
    with pytest.raises(ValueError, match="campaign_id"):
        JsonOrchestrationEventStore(tmp_path).load(campaign_id)
