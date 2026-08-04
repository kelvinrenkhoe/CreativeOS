"""Tests for bounded campaign orchestration policies and events."""

from datetime import UTC, datetime

import pytest

from api.campaign_orchestrator import CampaignOrchestratorAPI
from api.campaign_runner import CampaignRunnerResult


class StubRunner:
    def __init__(self, *results: CampaignRunnerResult) -> None:
        self.results = list(results)
        self.calls = []

    def advance(self, campaign_id: str, *, now=None) -> CampaignRunnerResult:
        self.calls.append((campaign_id, now))
        if not self.results:
            raise AssertionError("runner called more times than expected")
        return self.results.pop(0)


def result(
    *,
    stage: str = "ready",
    action: str = "queued",
    request_id: str | None = None,
    paused: bool = False,
    uncertain: bool = False,
    errors: tuple[str, ...] = (),
) -> CampaignRunnerResult:
    return CampaignRunnerResult(
        campaign_id="campaign-1",
        stage=stage,
        action=action,
        request_id=request_id,
        paused=paused,
        uncertain=uncertain,
        errors=errors,
    )


def test_once_advances_exactly_one_action() -> None:
    runner = StubRunner(result(action="production-started", request_id="request-1"))

    outcome = CampaignOrchestratorAPI(runner).run("campaign-1")

    assert outcome.steps == 1
    assert not outcome.completed
    assert len(runner.calls) == 1
    assert [event.kind for event in outcome.events] == [
        "campaign-started",
        "step-started",
        "step-completed",
    ]


def test_until_complete_runs_until_completion() -> None:
    runner = StubRunner(
        result(stage="ready", action="queued", request_id="request-1"),
        result(stage="in-production", action="execution-completed", request_id="request-1"),
        result(stage="completed", action="campaign-finished"),
    )

    outcome = CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-complete",
    )

    assert outcome.completed
    assert outcome.steps == 3
    assert outcome.events[-1].kind == "campaign-finished"
    assert len(runner.calls) == 3


def test_until_blocked_stops_on_pause() -> None:
    runner = StubRunner(
        result(action="queued", request_id="request-1"),
        result(action="awaiting-review", paused=True),
    )

    outcome = CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-blocked",
    )

    assert outcome.paused
    assert outcome.steps == 2
    assert outcome.events[-1].kind == "campaign-blocked"
    assert outcome.events[-1].detail == "runtime paused"


def test_errors_stop_orchestration_and_are_preserved() -> None:
    runner = StubRunner(result(errors=("provider unavailable",)))

    outcome = CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-complete",
    )

    assert outcome.errors == ("provider unavailable",)
    assert not outcome.successful
    assert [event.kind for event in outcome.events[-2:]] == [
        "step-failed",
        "campaign-blocked",
    ]


def test_uncertain_action_stops_orchestration() -> None:
    runner = StubRunner(result(action="provider-submitted", uncertain=True))

    outcome = CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-blocked",
    )

    assert outcome.uncertain
    assert outcome.events[-1].detail == "runtime action is uncertain"


def test_identical_results_stop_as_no_progress() -> None:
    repeated = result(action="waiting", request_id="request-1")
    runner = StubRunner(repeated, repeated)

    outcome = CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-complete",
    )

    assert outcome.steps == 2
    assert outcome.events[-1].kind == "campaign-stalled"
    assert outcome.warnings == (
        "orchestration stopped because the runner made no progress",
    )


def test_step_limit_bounds_orchestration() -> None:
    runner = StubRunner(
        result(action="one"),
        result(action="two"),
        result(action="three"),
    )

    outcome = CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-complete",
        max_steps=3,
    )

    assert outcome.steps == 3
    assert outcome.events[-1].kind == "campaign-step-limit-reached"
    assert outcome.warnings == ("orchestration stopped after max_steps=3",)


def test_same_reference_time_is_passed_to_every_step() -> None:
    reference = datetime(2026, 8, 4, 21, 30, tzinfo=UTC)
    runner = StubRunner(
        result(action="queued", request_id="request-1"),
        result(stage="completed", action="campaign-finished"),
    )

    CampaignOrchestratorAPI(runner).run(
        "campaign-1",
        policy="until-complete",
        now=reference,
    )

    assert runner.calls == [
        ("campaign-1", reference),
        ("campaign-1", reference),
    ]


@pytest.mark.parametrize("policy", ["", "forever", "until_done"])
def test_rejects_unsupported_policy(policy: str) -> None:
    with pytest.raises(ValueError, match="unsupported orchestration policy"):
        CampaignOrchestratorAPI(StubRunner()).run("campaign-1", policy=policy)


def test_rejects_non_positive_step_limit() -> None:
    with pytest.raises(ValueError, match="max_steps must be at least 1"):
        CampaignOrchestratorAPI(StubRunner()).run("campaign-1", max_steps=0)
