"""Domain models for deterministic campaign pipeline execution."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PipelineError(ValueError):
    """Raised when a campaign pipeline definition is invalid."""


class PipelineEventType(StrEnum):
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"


@dataclass(slots=True)
class ExecutionContext:
    """Mutable campaign-scoped values shared by pipeline stages."""

    campaign_id: str
    _values: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        campaign_id = self.campaign_id.strip()
        if not campaign_id:
            raise PipelineError("campaign_id must not be empty")
        self.campaign_id = campaign_id

    def set(self, key: str, value: Any) -> None:
        normalized = key.strip()
        if not normalized:
            raise PipelineError("context key must not be empty")
        self._values[normalized] = value

    def get(self, key: str) -> Any:
        try:
            return self._values[key]
        except KeyError as error:
            raise PipelineError(f"context value not found: {key}") from error

    def contains(self, key: str) -> bool:
        return key in self._values

    def snapshot(self) -> tuple[tuple[str, Any], ...]:
        return tuple(sorted(self._values.items(), key=lambda item: item[0]))


@dataclass(frozen=True, slots=True)
class PipelineStage:
    """A named executable stage and its stage dependencies."""

    name: str
    execute: Callable[[ExecutionContext], None]
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise PipelineError("stage name must not be empty")
        dependencies = tuple(dependency.strip() for dependency in self.dependencies)
        if any(not dependency for dependency in dependencies):
            raise PipelineError("stage dependencies must not be empty")
        if len(dependencies) != len(set(dependencies)):
            raise PipelineError("stage dependencies must be unique")
        if name in dependencies:
            raise PipelineError("a stage cannot depend on itself")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "dependencies", dependencies)


@dataclass(frozen=True, slots=True)
class ExecutionPlanEntry:
    stage_name: str
    order: int
    dependencies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    event_type: PipelineEventType
    stage_name: str
    message: str = ""


@dataclass(frozen=True, slots=True)
class PipelineResult:
    campaign_id: str
    plan: tuple[ExecutionPlanEntry, ...]
    completed_stages: tuple[str, ...]
    failed_stage: str | None
    events: tuple[PipelineEvent, ...]
    context_snapshot: tuple[tuple[str, Any], ...]

    @property
    def succeeded(self) -> bool:
        return self.failed_stage is None
