"""Tests for deterministic campaign execution reporting."""

from dataclasses import FrozenInstanceError

import pytest

from orchestrator import (
    CampaignExecutionEngine,
    ExecutionContext,
    PipelineError,
    PipelineRegistry,
    PipelineStage,
    StageExecutionStatus,
)


def _clock(*values: int):
    iterator = iter(values)
    return lambda: next(iterator)


def test_execution_report_records_order_and_stage_timing() -> None:
    registry = PipelineRegistry()
    registry.register(
        PipelineStage(
            "package",
            lambda context: context.set("package", "ready"),
            dependencies=("brief",),
        )
    )
    registry.register(
        PipelineStage("brief", lambda context: context.set("brief", "No Lose Guard"))
    )
    engine = CampaignExecutionEngine(
        registry,
        clock=_clock(100, 110, 115, 120, 130, 140),
    )

    report = engine.run(ExecutionContext("no-lose-guard"))

    assert report.succeeded is True
    assert report.completed_stages == ("brief", "package")
    assert report.failed_stage is None
    assert report.skipped_stages == ()
    assert report.total_duration_ms == 40
    assert tuple(record.duration_ms for record in report.stage_records) == (5, 10)
    assert all(
        record.status is StageExecutionStatus.COMPLETED
        for record in report.stage_records
    )


def test_execution_report_marks_remaining_stages_skipped_after_failure() -> None:
    def fail(_context: ExecutionContext) -> None:
        raise RuntimeError("caption provider unavailable")

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
    engine = CampaignExecutionEngine(
        registry,
        clock=_clock(0, 1, 2, 3, 5, 8),
    )

    report = engine.run(ExecutionContext("no-lose-guard"))

    assert report.succeeded is False
    assert report.completed_stages == ("brief",)
    assert report.failed_stage == "captions"
    assert report.skipped_stages == ("package",)
    assert tuple(record.status for record in report.stage_records) == (
        StageExecutionStatus.COMPLETED,
        StageExecutionStatus.FAILED,
        StageExecutionStatus.SKIPPED,
    )
    assert report.stage_records[1].message == "caption provider unavailable"
    assert report.stage_records[2].duration_ms == 0
    assert report.total_duration_ms == 8


def test_execution_report_is_immutable() -> None:
    registry = PipelineRegistry()
    registry.register(PipelineStage("brief", lambda _context: None))
    report = CampaignExecutionEngine(
        registry,
        clock=_clock(0, 1, 2, 3),
    ).run(ExecutionContext("no-lose-guard"))

    with pytest.raises(FrozenInstanceError):
        report.total_duration_ms = 99  # type: ignore[misc]


def test_registry_get_rejects_unknown_stage() -> None:
    registry = PipelineRegistry()

    with pytest.raises(PipelineError, match="stage not found"):
        registry.get("missing")
