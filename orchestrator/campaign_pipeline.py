"""Plan and execute deterministic campaign pipeline stages."""

from orchestrator.models import (
    ExecutionContext,
    ExecutionPlanEntry,
    PipelineError,
    PipelineEvent,
    PipelineEventType,
    PipelineResult,
    PipelineStage,
)


class PipelineRegistry:
    """Register uniquely named campaign pipeline stages."""

    def __init__(self) -> None:
        self._stages: dict[str, PipelineStage] = {}

    def register(self, stage: PipelineStage) -> None:
        if stage.name in self._stages:
            raise PipelineError(f"pipeline stage already registered: {stage.name}")
        self._stages[stage.name] = stage

    def stages(self) -> tuple[PipelineStage, ...]:
        return tuple(self._stages[name] for name in sorted(self._stages))


class CampaignPipeline:
    """Build an execution plan and run stages sequentially."""

    def __init__(self, registry: PipelineRegistry) -> None:
        self._registry = registry

    def plan(self) -> tuple[ExecutionPlanEntry, ...]:
        stages = {stage.name: stage for stage in self._registry.stages()}
        if not stages:
            raise PipelineError("pipeline must contain at least one stage")

        known_names = set(stages)
        for stage in stages.values():
            missing = sorted(set(stage.dependencies) - known_names)
            if missing:
                names = ", ".join(missing)
                raise PipelineError(f"stage {stage.name} has missing dependencies: {names}")

        remaining = set(stages)
        completed: set[str] = set()
        ordered: list[PipelineStage] = []
        while remaining:
            ready = sorted(
                name for name in remaining if set(stages[name].dependencies).issubset(completed)
            )
            if not ready:
                names = ", ".join(sorted(remaining))
                raise PipelineError(f"pipeline dependency cycle detected: {names}")
            for name in ready:
                ordered.append(stages[name])
                completed.add(name)
                remaining.remove(name)

        return tuple(
            ExecutionPlanEntry(
                stage_name=stage.name,
                order=index,
                dependencies=stage.dependencies,
            )
            for index, stage in enumerate(ordered, start=1)
        )

    def run(self, context: ExecutionContext) -> PipelineResult:
        plan = self.plan()
        stages = {stage.name: stage for stage in self._registry.stages()}
        completed: list[str] = []
        events: list[PipelineEvent] = []
        failed_stage: str | None = None

        for entry in plan:
            stage = stages[entry.stage_name]
            events.append(PipelineEvent(PipelineEventType.STAGE_STARTED, stage.name))
            try:
                stage.execute(context)
            except Exception as error:  # noqa: BLE001
                failed_stage = stage.name
                events.append(
                    PipelineEvent(
                        PipelineEventType.STAGE_FAILED,
                        stage.name,
                        str(error),
                    )
                )
                break
            completed.append(stage.name)
            events.append(PipelineEvent(PipelineEventType.STAGE_COMPLETED, stage.name))

        return PipelineResult(
            campaign_id=context.campaign_id,
            plan=plan,
            completed_stages=tuple(completed),
            failed_stage=failed_stage,
            events=tuple(events),
            context_snapshot=context.snapshot(),
        )
