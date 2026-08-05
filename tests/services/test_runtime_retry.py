"""Tests for deterministic runtime retry execution."""

import pytest

from services.runtime_retry import (
    RetryableRuntimeError,
    RetryExhaustedError,
    RetryPolicy,
    RuntimeRetryEngine,
)


def test_first_attempt_success_does_not_sleep() -> None:
    delays: list[float] = []
    result = RuntimeRetryEngine(sleeper=delays.append).run(lambda: "ok")

    assert result.value == "ok"
    assert result.recovered is False
    assert [attempt.succeeded for attempt in result.attempts] == [True]
    assert delays == []


def test_retryable_failure_then_success_records_attempts_and_delay() -> None:
    calls = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RetryableRuntimeError("temporary")
        return "recovered"

    result = RuntimeRetryEngine(sleeper=delays.append).run(operation)

    assert result.value == "recovered"
    assert result.recovered is True
    assert [attempt.succeeded for attempt in result.attempts] == [False, True]
    assert result.attempts[0].error_message == "temporary"
    assert delays == [1.0]


def test_exponential_delays_are_deterministic() -> None:
    calls = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 4:
            raise RetryableRuntimeError("again")
        return "ok"

    policy = RetryPolicy(max_attempts=4, initial_delay=2, multiplier=3)
    result = RuntimeRetryEngine(policy, sleeper=delays.append).run(operation)

    assert result.value == "ok"
    assert delays == [2, 6, 18]
    assert [attempt.delay_before for attempt in result.attempts] == [0, 2, 6, 18]


def test_max_delay_caps_backoff() -> None:
    policy = RetryPolicy(max_attempts=4, initial_delay=2, multiplier=3, max_delay=5)

    assert policy.delay_before(2) == 2
    assert policy.delay_before(3) == 5
    assert policy.delay_before(4) == 5


def test_exhaustion_preserves_complete_attempt_history() -> None:
    engine = RuntimeRetryEngine(RetryPolicy(max_attempts=3), sleeper=lambda _: None)

    with pytest.raises(RetryExhaustedError) as captured:
        engine.run(lambda: (_ for _ in ()).throw(RetryableRuntimeError("offline")))

    assert len(captured.value.attempts) == 3
    assert all(not attempt.succeeded for attempt in captured.value.attempts)
    assert isinstance(captured.value.cause, RetryableRuntimeError)


def test_non_retryable_failure_is_raised_immediately() -> None:
    delays: list[float] = []
    engine = RuntimeRetryEngine(sleeper=delays.append)

    with pytest.raises(ValueError, match="invalid"):
        engine.run(lambda: (_ for _ in ()).throw(ValueError("invalid")))

    assert delays == []


@pytest.mark.parametrize(
    ("policy", "message"),
    [
        (lambda: RetryPolicy(max_attempts=0), "max_attempts"),
        (lambda: RetryPolicy(initial_delay=-1), "initial_delay"),
        (lambda: RetryPolicy(multiplier=0.5), "multiplier"),
        (lambda: RetryPolicy(max_delay=-1), "max_delay"),
    ],
)
def test_invalid_policy_values_are_rejected(policy, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        policy()


def test_delay_before_rejects_first_attempt() -> None:
    with pytest.raises(ValueError, match="retry attempt"):
        RetryPolicy().delay_before(1)
