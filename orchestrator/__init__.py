"""Campaign pipeline orchestration public API."""

from orchestrator.campaign_pipeline import CampaignPipeline, PipelineRegistry
from orchestrator.execution import (
    CampaignExecutionReport,
    StageExecutionRecord,
    StageExecutionStatus,
)
from orchestrator.execution_engine import CampaignExecutionEngine
from orchestrator.models import (
    ExecutionContext,
    ExecutionPlanEntry,
    PipelineError,
    PipelineEvent,
    PipelineEventType,
    PipelineResult,
    PipelineStage,
)
from orchestrator.presets import (
    CampaignRuntimePreset,
    CampaignRuntimePresetRegistry,
    music_release_preset,
)
from orchestrator.runtime import CampaignRuntimeBuilder, RuntimeStage

__all__ = [
    "CampaignExecutionEngine",
    "CampaignExecutionReport",
    "CampaignPipeline",
    "CampaignRuntimeBuilder",
    "CampaignRuntimePreset",
    "CampaignRuntimePresetRegistry",
    "ExecutionContext",
    "ExecutionPlanEntry",
    "PipelineError",
    "PipelineEvent",
    "PipelineEventType",
    "PipelineRegistry",
    "PipelineResult",
    "PipelineStage",
    "RuntimeStage",
    "StageExecutionRecord",
    "StageExecutionStatus",
    "music_release_preset",
]
