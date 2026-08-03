"""Immutable models for deterministic campaign execution reporting."""

from dataclasses import dataclass
from enum import StrEnum

from orchestrator.models import ExecutionPlanEntry, PipelineError


class StageExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class StageExecutionRecord:
    stage_name: str
    status: StageExecutionStatus
    started_ms: int | None
    finished_ms: int | None
    duration_ms: int
    message: str = ""

    def __post_init__(self) -> None:
        if not self.stage_name.strip():
            raise PipelineError("stage_name must not be empty")
        if self.duration_ms < 0:
            raise PipelineError("duration_ms must not be negative")
        if self.status is StageExecutionStatus.SKIPPED:
            if self.started_ms is not None or self.finished_ms is not None:
                raise PipelineError("skipped stages must not contain timing values")
            if self.duration_ms != 0:
                raise PipelineError("skipped stages must have zero duration")
            return
        if self.started_ms is None or self.finished_ms is None:
            raise PipelineError("executed stages must contain timing values")
        if self.finished_ms < self.started_ms:
            raise PipelineError("finished_ms must not precede started_ms")
        if self.duration_ms != self.finished_ms - self.started_ms:
            raise PipelineError("duration_ms must match stage timing values")


@dataclass(frozen=True, slots=True)
class CampaignExecutionReport:
    campaign_id: str
    plan: tuple[ExecutionPlanEntry, ...]
    stage_records: tuple[StageExecutionRecord, ...]
    started_ms: int
    finished_ms: int
    total_duration_ms: int

    def __post_init__(self) -> None:
        if not self.campaign_id.strip():
            raise PipelineError("campaign_id must not be empty")
        if self.finished_ms < self.started_ms:
            raise PipelineError("finished_ms must not precede started_ms")
        if self.total_duration_ms != self.finished_ms - self.started_ms:
            raise PipelineError("total_duration_ms must match report timing values")
        planned = tuple(entry.stage_name for entry in self.plan)
        recorded = tuple(record.stage_name for record in self.stage_records)
        if planned != recorded:
            raise PipelineError("stage records must match execution plan order")

    @property
    def succeeded(self) -> bool:
        return all(record.status is not StageExecutionStatus.FAILED for record in self.stage_records)

    @property
    def completed_stages(self) -> tuple[str, ...]:
        return tuple(
            record.stage_name
            for record in self.stage_records
            if record.status is StageExecutionStatus.COMPLETED
        )

    @property
    def failed_stage(self) -> str | None:
        for record in self.stage_records:
            if record.status is StageExecutionStatus.FAILED:
                return record.stage_name
        return None

    @property
    def skipped_stages(self) -> tuple[str, ...]:
        return tuple(
            record.stage_name
            for record in self.stage_records
            if record.status is StageExecutionStatus.SKIPPED
        )
