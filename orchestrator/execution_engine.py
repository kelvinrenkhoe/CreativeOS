"""Execute campaign stages with deterministic timing and reporting."""

from collections.abc import Callable
from time import monotonic_ns

from orchestrator.campaign_pipeline import CampaignPipeline, PipelineRegistry
from orchestrator.execution import (
    CampaignExecutionReport,
    StageExecutionRecord,
    StageExecutionStatus,
)
from orchestrator.models import ExecutionContext

Clock = Callable[[], int]


def _monotonic_milliseconds() -> int:
    return monotonic_ns() // 1_000_000


class CampaignExecutionEngine:
    """Run a planned campaign pipeline and capture immutable stage outcomes."""

    def __init__(
        self,
        registry: PipelineRegistry,
        *,
        clock: Clock = _monotonic_milliseconds,
    ) -> None:
        self._registry = registry
        self._pipeline = CampaignPipeline(registry)
        self._clock = clock

    def run(self, context: ExecutionContext) -> CampaignExecutionReport:
        plan = self._pipeline.plan()
        report_started = self._clock()
        records: list[StageExecutionRecord] = []
        failed = False

        for entry in plan:
            if failed:
                records.append(
                    StageExecutionRecord(
                        stage_name=entry.stage_name,
                        status=StageExecutionStatus.SKIPPED,
                        started_ms=None,
                        finished_ms=None,
                        duration_ms=0,
                        message="skipped after earlier stage failure",
                    )
                )
                continue

            stage = self._registry.get(entry.stage_name)
            stage_started = self._clock()
            try:
                stage.execute(context)
            except Exception as error:  # noqa: BLE001
                stage_finished = self._clock()
                records.append(
                    StageExecutionRecord(
                        stage_name=stage.name,
                        status=StageExecutionStatus.FAILED,
                        started_ms=stage_started,
                        finished_ms=stage_finished,
                        duration_ms=stage_finished - stage_started,
                        message=str(error),
                    )
                )
                failed = True
                continue

            stage_finished = self._clock()
            records.append(
                StageExecutionRecord(
                    stage_name=stage.name,
                    status=StageExecutionStatus.COMPLETED,
                    started_ms=stage_started,
                    finished_ms=stage_finished,
                    duration_ms=stage_finished - stage_started,
                )
            )

        report_finished = self._clock()
        return CampaignExecutionReport(
            campaign_id=context.campaign_id,
            plan=plan,
            stage_records=tuple(records),
            started_ms=report_started,
            finished_ms=report_finished,
            total_duration_ms=report_finished - report_started,
        )
