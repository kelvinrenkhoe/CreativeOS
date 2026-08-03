"""Compose existing campaign capabilities into the execution runtime."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from orchestrator.campaign_pipeline import PipelineRegistry
from orchestrator.models import ExecutionContext, PipelineError, PipelineStage

StageHandler = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class RuntimeStage:
    """Describe one context-backed campaign runtime stage."""

    name: str
    handler: StageHandler
    input_keys: tuple[str, ...]
    output_key: str
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise PipelineError("runtime stage name must not be empty")
        if not self.output_key.strip():
            raise PipelineError("runtime stage output_key must not be empty")
        if any(not key.strip() for key in self.input_keys):
            raise PipelineError("runtime stage input keys must not be empty")
        if len(self.input_keys) != len(set(self.input_keys)):
            raise PipelineError("runtime stage input keys must be unique")

    def execute(self, context: ExecutionContext) -> None:
        missing = tuple(key for key in self.input_keys if not context.contains(key))
        if missing:
            names = ", ".join(missing)
            raise PipelineError(f"runtime stage {self.name} missing context values: {names}")
        inputs = tuple(context.get(key) for key in self.input_keys)
        context.set(self.output_key, self.handler(*inputs))

    def to_pipeline_stage(self) -> PipelineStage:
        return PipelineStage(
            name=self.name,
            execute=self.execute,
            dependencies=self.dependencies,
        )


class CampaignRuntimeBuilder:
    """Build a deterministic registry from ordered runtime stage definitions."""

    def __init__(self, stages: tuple[RuntimeStage, ...]) -> None:
        if not stages:
            raise PipelineError("campaign runtime must contain at least one stage")
        self._stages = stages

    def build_registry(self) -> PipelineRegistry:
        registry = PipelineRegistry()
        for stage in self._stages:
            registry.register(stage.to_pipeline_stage())
        return registry
