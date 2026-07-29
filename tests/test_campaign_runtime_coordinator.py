from dataclasses import dataclass
from datetime import UTC, datetime

from services.campaign_orchestration import (
    CampaignOrchestrationService,
    WorkflowEvidence,
)
from services.campaign_planner import CampaignIntent, CampaignPhaseDirection, CampaignPlan
from services.campaign_queue import CampaignQueueService, ExecutionQueue
from services.campaign_run_state import JsonCampaignRunStore
from services.campaign_runtime_coordinator import CampaignRuntimeCoordinator
from services.operations_dashboard import AuditHistory
from services.provider_execution import (
    ExecutionApproval,
    ExecutionReceipt,
    ExecutionRequest,
)
from services.runtime_checkpoints import (
    CheckpointedCampaignRuntime,
    JsonRuntimeCheckpointStore,
)
from story.context import StoryContext
from story.models import Character, CreativeWork, Location, Symbol, Theme

NOW = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


@dataclass
class FakeAdapter:
    provider: str = "open-video"
    media_types: tuple[str, ...] = ("video",)
    calls: int = 0

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        return ()

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        self.calls += 1
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id=f"generated-{request.request_id}",
        )


def prepared():
    context = StoryContext(
        universe_id="kelvin-rankie",
        universe_name="Kelvin Rankie Universe",
        work=CreativeWork(id="no-lose-guard", name="No Lose Guard", kind="song"),
        themes=(Theme(id="resilience", name="Resilience"),),
        characters=(Character(id="kelvin", name="Kelvin"),),
        locations=(Location(id="studio", name="Studio"),),
        symbols=(Symbol(id="light", name="Light"),),
        arcs=(),
        relationships=(),
        knowledge="",
    )
    plan = CampaignPlan(
        work_id="no-lose-guard",
        work_name="No Lose Guard",
        total_weeks=2,
        intent=CampaignIntent(
            objective="Build release awareness",
            audience="Afrobeats listeners",
            tone="Cinematic and resilient",
            platforms=("instagram",),
        ),
        phases=(
            CampaignPhaseDirection(
                phase_number=1,
                phase_id="awakening",
                title="The Awakening",
                start_week=1,
                end_week=2,
                narrative_objective="Reveal renewed determination.",
                campaign_objective="Build release awareness",
                audience="Afrobeats listeners",
                tone="Cinematic and resilient",
                platforms=("instagram",),
            ),
        ),
    )
    return CampaignOrchestrationService().prepare("no-lose-guard-launch", context, plan)


def queued(work_id: str = "no-lose-guard", request_id: str = "video-01"):
    request = ExecutionRequest(
        request_id=request_id,
        asset_id=f"{work_id}-video",
        work_id=work_id,
        media_type="video",
        provider="open-video",
        prompt="A cinematic performance scene.",
    )
    return CampaignQueueService().schedule(
        ExecutionQueue(),
        request,
        ExecutionApproval(
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            approved_by="Kelvin",
        ),
        scheduled_for=NOW,
    )


def coordinator(tmp_path, *, stage: str = "planned"):
    store = JsonCampaignRunStore(tmp_path)
    run = prepared()
    service = CampaignOrchestrationService()
    if stage != "planned":
        run = service.advance(run, "in-production")
    store.save(run)
    return CampaignRuntimeCoordinator(), store


def test_starts_production_and_persists_one_transition(tmp_path) -> None:
    service, store = coordinator(tmp_path)

    result = service.advance(
        "no-lose-guard-launch",
        store,
        ExecutionQueue(),
        AuditHistory(),
        (),
        worker_id="worker-1",
        now=NOW,
    )

    assert result.action == "production-started"
    assert result.run.stage == "in-production"
    assert store.load("no-lose-guard-launch").stage == "in-production"


def test_executes_only_one_job_for_the_campaign(tmp_path) -> None:
    service, store = coordinator(tmp_path, stage="in-production")
    other = queued("another-song", "other-video").jobs[0]
    queue = ExecutionQueue(jobs=(other, *queued().jobs))
    adapter = FakeAdapter()

    result = service.advance(
        "no-lose-guard-launch",
        store,
        queue,
        AuditHistory(),
        (adapter,),
        worker_id="worker-1",
        now=NOW,
    )

    statuses = {job.request.request_id: job.status for job in result.queue.jobs}
    assert result.action == "execution-completed"
    assert result.request_id == "video-01"
    assert statuses == {"other-video": "scheduled", "video-01": "completed"}
    assert store.load("no-lose-guard-launch").stage == "in-production"
    assert adapter.calls == 1


def test_waits_for_human_asset_approval_after_production(tmp_path) -> None:
    service, store = coordinator(tmp_path, stage="in-production")

    result = service.advance(
        "no-lose-guard-launch",
        store,
        ExecutionQueue(),
        AuditHistory(),
        (),
        worker_id="worker-1",
        now=NOW,
    )

    assert result.action == "awaiting-approved-assets"
    assert result.paused is True
    assert store.load("no-lose-guard-launch").stage == "in-production"


def test_does_not_accept_asset_approval_while_work_is_open(tmp_path) -> None:
    service, store = coordinator(tmp_path, stage="in-production")
    evidence = WorkflowEvidence("approved-assets", "approval-1", "Kelvin")

    result = service.advance(
        "no-lose-guard-launch",
        store,
        queued(),
        AuditHistory(),
        (),
        worker_id="worker-1",
        now=NOW,
        evidence=evidence,
    )

    assert result.action == "awaiting-production"
    assert store.load("no-lose-guard-launch").stage == "in-production"


def test_requires_explicit_publication_and_measurement_evidence(tmp_path) -> None:
    service, store = coordinator(tmp_path, stage="in-production")
    history = AuditHistory()
    empty = ExecutionQueue()

    ready = service.advance(
        "no-lose-guard-launch",
        store,
        empty,
        history,
        (),
        worker_id="worker-1",
        now=NOW,
        evidence=WorkflowEvidence("approved-assets", "approval-1", "Kelvin"),
    )
    waiting = service.advance(
        "no-lose-guard-launch",
        store,
        empty,
        history,
        (),
        worker_id="worker-1",
        now=NOW,
    )
    published = service.advance(
        "no-lose-guard-launch",
        store,
        empty,
        history,
        (),
        worker_id="worker-1",
        now=NOW,
        evidence=WorkflowEvidence("publication-receipt", "post-1", "Kelvin"),
    )
    measured = service.advance(
        "no-lose-guard-launch",
        store,
        empty,
        history,
        (),
        worker_id="worker-1",
        now=NOW,
        evidence=WorkflowEvidence("campaign-measurement", "metrics-1", "Kelvin"),
    )

    assert ready.run.stage == "ready"
    assert waiting.action == "awaiting-publication"
    assert published.run.stage == "published"
    assert measured.run.stage == "measured"
    assert [item.kind for item in measured.run.evidence] == [
        "approved-assets",
        "publication-receipt",
        "campaign-measurement",
    ]


def test_completes_measured_campaign_once_and_then_stops(tmp_path) -> None:
    service, store = coordinator(tmp_path, stage="in-production")
    orchestration = CampaignOrchestrationService()
    run = store.load("no-lose-guard-launch")
    run = orchestration.advance(
        run,
        "ready",
        evidence=WorkflowEvidence("approved-assets", "approval-1", "Kelvin"),
    )
    run = orchestration.advance(
        run,
        "published",
        evidence=WorkflowEvidence("publication-receipt", "post-1", "Kelvin"),
    )
    run = orchestration.advance(
        run,
        "measured",
        evidence=WorkflowEvidence("campaign-measurement", "metrics-1", "Kelvin"),
    )
    store.save(run)

    completed = service.advance(
        "no-lose-guard-launch",
        store,
        ExecutionQueue(),
        AuditHistory(),
        (),
        worker_id="worker-1",
        now=NOW,
    )
    stopped = service.advance(
        "no-lose-guard-launch",
        store,
        ExecutionQueue(),
        AuditHistory(),
        (),
        worker_id="worker-1",
        now=NOW,
    )

    assert completed.run.stage == "completed"
    assert stopped.action == "completed"
    assert stopped.run == completed.run


def test_checkpoint_prevents_duplicate_provider_execution_after_restart(tmp_path) -> None:
    _, run_store = coordinator(tmp_path / "runs", stage="in-production")
    checkpoint_path = tmp_path / "runtime-checkpoints.json"
    queue = queued()
    adapter = FakeAdapter()

    first = CheckpointedCampaignRuntime().advance(
        "no-lose-guard-launch",
        run_store,
        JsonRuntimeCheckpointStore(checkpoint_path),
        queue,
        AuditHistory(),
        (adapter,),
        worker_id="worker-1",
        now=NOW,
    )
    replayed = CheckpointedCampaignRuntime().advance(
        "no-lose-guard-launch",
        run_store,
        JsonRuntimeCheckpointStore(checkpoint_path),
        queue,
        AuditHistory(),
        (adapter,),
        worker_id="worker-2",
        now=NOW,
    )

    assert first.result is not None
    assert first.result.action == "execution-completed"
    assert first.checkpoint is not None
    assert first.checkpoint.status == "completed"
    assert replayed.result is None
    assert replayed.replayed is True
    assert replayed.checkpoint == first.checkpoint
    assert adapter.calls == 1


def test_started_checkpoint_becomes_uncertain_after_restart(tmp_path) -> None:
    path = tmp_path / "runtime-checkpoints.json"
    first_store = JsonRuntimeCheckpointStore(path)
    started, acquired = first_store.begin(
        campaign_id="no-lose-guard-launch",
        action_key="execution:video-01",
        now=NOW,
    )

    recovered, reacquired = JsonRuntimeCheckpointStore(path).begin(
        campaign_id="no-lose-guard-launch",
        action_key="execution:video-01",
        now=NOW,
    )

    assert acquired is True
    assert started.status == "started"
    assert reacquired is False
    assert recovered.status == "uncertain"
    assert JsonRuntimeCheckpointStore(path).load() == (recovered,)


def test_uncertain_checkpoint_never_retries_provider_work(tmp_path) -> None:
    _, run_store = coordinator(tmp_path / "runs", stage="in-production")
    checkpoint_store = JsonRuntimeCheckpointStore(tmp_path / "runtime-checkpoints.json")
    checkpoint_store.begin(
        campaign_id="no-lose-guard-launch",
        action_key="execution:video-01",
        now=NOW,
    )
    adapter = FakeAdapter()

    result = CheckpointedCampaignRuntime().advance(
        "no-lose-guard-launch",
        run_store,
        checkpoint_store,
        queued(),
        AuditHistory(),
        (adapter,),
        worker_id="worker-2",
        now=NOW,
    )

    assert result.uncertain is True
    assert result.replayed is True
    assert result.result is None
    assert adapter.calls == 0


def test_unfinished_prior_stage_blocks_later_stage_after_restart(tmp_path) -> None:
    _, run_store = coordinator(tmp_path / "runs")
    checkpoint_store = JsonRuntimeCheckpointStore(tmp_path / "runtime-checkpoints.json")
    checkpoint_store.begin(
        campaign_id="no-lose-guard-launch",
        action_key="stage:planned",
        now=NOW,
    )
    run = run_store.load("no-lose-guard-launch")
    run_store.save(CampaignOrchestrationService().advance(run, "in-production"))
    adapter = FakeAdapter()

    result = CheckpointedCampaignRuntime().advance(
        "no-lose-guard-launch",
        run_store,
        checkpoint_store,
        queued(),
        AuditHistory(),
        (adapter,),
        worker_id="worker-2",
        now=NOW,
    )

    assert result.uncertain is True
    assert result.checkpoint is not None
    assert result.checkpoint.action_key == "stage:planned"
    assert result.result is None
    assert adapter.calls == 0


def test_paused_runtime_does_not_block_newly_approved_work(tmp_path) -> None:
    _, run_store = coordinator(tmp_path / "runs", stage="in-production")
    checkpoint_store = JsonRuntimeCheckpointStore(tmp_path / "runtime-checkpoints.json")
    runtime = CheckpointedCampaignRuntime()
    adapter = FakeAdapter()

    paused = runtime.advance(
        "no-lose-guard-launch",
        run_store,
        checkpoint_store,
        ExecutionQueue(),
        AuditHistory(),
        (adapter,),
        worker_id="worker-1",
        now=NOW,
    )
    resumed = runtime.advance(
        "no-lose-guard-launch",
        run_store,
        checkpoint_store,
        queued(),
        AuditHistory(),
        (adapter,),
        worker_id="worker-1",
        now=NOW,
    )

    assert paused.checkpoint is None
    assert paused.result is not None
    assert paused.result.action == "awaiting-approved-assets"
    assert resumed.result is not None
    assert resumed.result.action == "execution-completed"
    assert adapter.calls == 1
