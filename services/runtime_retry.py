"""Deterministic retry policy and execution for transient runtime failures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import Generic, TypeVar

T = TypeVar("T")


class RetryableRuntimeError(RuntimeError):
    """Marker error for failures that may be retried safely."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded exponential-backoff retry settings."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    multiplier: float = 2.0
    max_delay: float | None = None

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1")
        if self.max_delay is not None and self.max_delay < 0:
            raise ValueError("max_delay must be non-negative")

    def delay_before(self, attempt: int) -> float:
        """Return the delay before a one-based retry attempt."""
        if attempt < 2:
            raise ValueError("retry attempt must be at least 2")
        delay = self.initial_delay * self.multiplier ** (attempt - 2)
        return min(delay, self.max_delay) if self.max_delay is not None else delay


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """One completed operation attempt."""

    number: int
    succeeded: bool
    error_type: str | None = None
    error_message: str | None = None
    delay_before: float = 0.0


@dataclass(frozen=True, slots=True)
class RetryResult(Generic[T]):
    """Successful result plus complete attempt history."""

    value: T
    attempts: tuple[RetryAttempt, ...]

    @property
    def recovered(self) -> bool:
        return len(self.attempts) > 1


class RetryExhaustedError(RetryableRuntimeError):
    """Raised after all retry attempts fail."""

    def __init__(self, attempts: tuple[RetryAttempt, ...], cause: BaseException) -> None:
        super().__init__(f"retry attempts exhausted after {len(attempts)} attempts: {cause}")
        self.attempts = attempts
        self.cause = cause


class RuntimeRetryEngine:
    """Execute retryable operations with injected sleeping for deterministic tests."""

    def __init__(
        self,
        policy: RetryPolicy | None = None,
        *,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.policy = policy or RetryPolicy()
        self.sleeper = sleeper

    def run(self, operation: Callable[[], T]) -> RetryResult[T]:
        attempts: list[RetryAttempt] = []
        for number in range(1, self.policy.max_attempts + 1):
            delay = 0.0
            if number > 1:
                delay = self.policy.delay_before(number)
                self.sleeper(delay)
            try:
                value = operation()
            except RetryableRuntimeError as exc:
                attempts.append(
                    RetryAttempt(number, False, type(exc).__name__, str(exc), delay)
                )
                if number == self.policy.max_attempts:
                    raise RetryExhaustedError(tuple(attempts), exc) from exc
            except Exception:
                raise
            else:
                attempts.append(RetryAttempt(number, True, delay_before=delay))
                return RetryResult(value, tuple(attempts))
        raise AssertionError("retry loop completed unexpectedly")
