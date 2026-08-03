"""Tests for context-backed end-to-end campaign runtime stages."""

import pytest

from orchestrator import (
    CampaignExecutionEngine,
    CampaignRuntimeBuilder,
    ExecutionContext,
    PipelineError,
    RuntimeStage,
)


def _clock(*values: int):
    iterator = iter(values)
    return lambda: next(iterator)


def test_runtime_executes_real_campaign_sequence_through_context() -> None:
    stages = (
        RuntimeStage("brief", lambda campaign: f"brief:{campaign}", ("campaign",), "brief"),
        RuntimeStage(
            "captions",
            lambda brief: f"captions:{brief}",
            ("brief",),
            "captions",
            dependencies=("brief",),
        ),
        RuntimeStage(
            "package",
            lambda brief, captions: f"package:{brief}|{captions}",
            ("brief", "captions"),
            "package",
            dependencies=("brief", "captions"),
        ),
    )
    context = ExecutionContext("no-lose-guard")
    context.set("campaign", "No Lose Guard")
    engine = CampaignExecutionEngine(
        CampaignRuntimeBuilder(stages).build_registry(),
        clock=_clock(0, 1, 2, 3, 4, 5, 6, 7),
    )

    report = engine.run(context)

    assert report.succeeded is True
    assert report.completed_stages == ("brief", "captions", "package")
    assert context.get("package") == (
        "package:brief:No Lose Guard|captions:brief:No Lose Guard"
    )


def test_runtime_stage_reports_missing_context_values() -> None:
    stage = RuntimeStage("captions", lambda brief: brief, ("brief",), "captions")

    with pytest.raises(PipelineError, match="missing context values: brief"):
        stage.execute(ExecutionContext("no-lose-guard"))


def test_runtime_builder_preserves_dependency_planning() -> None:
    stages = (
        RuntimeStage("package", lambda captions: captions, ("captions",), "package", ("captions",)),
        RuntimeStage("brief", lambda campaign: campaign, ("campaign",), "brief"),
        RuntimeStage("captions", lambda brief: brief, ("brief",), "captions", ("brief",)),
    )
    registry = CampaignRuntimeBuilder(stages).build_registry()
    context = ExecutionContext("no-lose-guard")
    context.set("campaign", "No Lose Guard")
    report = CampaignExecutionEngine(
        registry,
        clock=_clock(0, 1, 2, 3, 4, 5, 6, 7),
    ).run(context)

    assert report.completed_stages == ("brief", "captions", "package")


def test_runtime_stage_definition_rejects_duplicate_inputs() -> None:
    with pytest.raises(PipelineError, match="input keys must be unique"):
        RuntimeStage("captions", lambda *_values: None, ("brief", "brief"), "captions")
