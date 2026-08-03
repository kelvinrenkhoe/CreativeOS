"""Tests for deterministic campaign pipeline planning and execution."""

import pytest

from orchestrator import (
    CampaignPipeline,
    ExecutionContext,
    PipelineError,
    PipelineEventType,
    PipelineRegistry,
    PipelineStage,
)


def test_pipeline_orders_dependencies_and_propagates_context() -> None:
    registry = PipelineRegistry()
    registry.register(
        PipelineStage(
            "package",
            lambda context: context.set("package", "ready"),
            dependencies=("brief", "captions"),
        )
    )
    registry.register(
        PipelineStage(
            "captions",
            lambda context: context.set("captions", context.get("brief") + " captions"),
            dependencies=("brief",),
        )
    )
    registry.register(PipelineStage("brief", lambda context: context.set("brief", "No Lose Guard")))

    context = ExecutionContext("no-lose-guard")
    result = CampaignPipeline(registry).run(context)

    assert tuple(entry.stage_name for entry in result.plan) == (
        "brief",
        "captions",
        "package",
    )
    assert result.completed_stages == ("brief", "captions", "package")
    assert result.succeeded is True
    assert context.get("captions") == "No Lose Guard captions"
    assert context.get("package") == "ready"
    assert tuple(event.event_type for event in result.events) == (
        PipelineEventType.STAGE_STARTED,
        PipelineEventType.STAGE_COMPLETED,
        PipelineEventType.STAGE_STARTED,
        PipelineEventType.STAGE_COMPLETED,
        PipelineEventType.STAGE_STARTED,
        PipelineEventType.STAGE_COMPLETED,
    )


def test_pipeline_stops_after_stage_failure() -> None:
    def fail(_context: ExecutionContext) -> None:
        raise RuntimeError("generator unavailable")

    registry = PipelineRegistry()
    registry.register(PipelineStage("brief", lambda context: context.set("brief", "ready")))
    registry.register(PipelineStage("captions", fail, dependencies=("brief",)))
    registry.register(
        PipelineStage(
            "package",
            lambda context: context.set("package", "ready"),
            dependencies=("captions",),
        )
    )

    result = CampaignPipeline(registry).run(ExecutionContext("no-lose-guard"))

    assert result.succeeded is False
    assert result.failed_stage == "captions"
    assert result.completed_stages == ("brief",)
    assert result.events[-1].event_type is PipelineEventType.STAGE_FAILED
    assert result.events[-1].message == "generator unavailable"
    assert "package" not in result.completed_stages


def test_registry_rejects_duplicate_stage_names() -> None:
    registry = PipelineRegistry()
    registry.register(PipelineStage("brief", lambda _context: None))

    with pytest.raises(PipelineError, match="already registered"):
        registry.register(PipelineStage("brief", lambda _context: None))


def test_plan_rejects_missing_dependency() -> None:
    registry = PipelineRegistry()
    registry.register(PipelineStage("captions", lambda _context: None, dependencies=("brief",)))

    with pytest.raises(PipelineError, match="missing dependencies"):
        CampaignPipeline(registry).plan()


def test_plan_rejects_dependency_cycle() -> None:
    registry = PipelineRegistry()
    registry.register(PipelineStage("brief", lambda _context: None, dependencies=("press",)))
    registry.register(PipelineStage("press", lambda _context: None, dependencies=("brief",)))

    with pytest.raises(PipelineError, match="cycle detected"):
        CampaignPipeline(registry).plan()


def test_context_snapshot_is_stably_sorted() -> None:
    context = ExecutionContext("no-lose-guard")
    context.set("storyboard", "ready")
    context.set("brief", "ready")

    assert context.snapshot() == (("brief", "ready"), ("storyboard", "ready"))
