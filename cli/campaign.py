"""Campaign commands for CreativeOS."""

from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai.manager import AIManager
from core.config import ConfigurationError
from core.project import Project
from services.audit_history_store import AuditHistoryStateError, JsonAuditHistoryStore
from services.campaign import CampaignService
from services.campaign_generator import CampaignGeneratorService
from services.campaign_queue import CampaignQueueService
from services.campaign_run_state import CampaignRunStateError, JsonCampaignRunStore
from services.human_review_inbox import (
    HumanReviewInboxService,
    ReviewDecision,
    ReviewInbox,
)
from services.operations_dashboard import (
    AuditEvent,
    AuditHistory,
    AuditHistoryService,
    OperationsDashboardService,
)
from services.persistent_queue import (
    JsonExecutionQueueStore,
    PersistentQueue,
    QueueStateError,
)
from services.review_decision_store import (
    JsonReviewDecisionStore,
    ReviewDecisionStateError,
)
from services.scheduled_analytics_refresh import (
    JsonAnalyticsRefreshStore,
    ScheduledAnalyticsRefreshError,
)
from services.runtime_checkpoints import (
    CheckpointedCampaignRuntime,
    JsonRuntimeCheckpointStore,
    RuntimeCheckpointError,
)

app = typer.Typer(help="Create and manage music marketing campaigns.", no_args_is_help=True)
console = Console()
RUNTIME_PATH = Path(".creativeos") / "runtime"
CAMPAIGN_RUNS_PATH = RUNTIME_PATH / "campaign-runs"
QUEUE_PATH = RUNTIME_PATH / "execution-queue.json"
AUDIT_HISTORY_PATH = RUNTIME_PATH / "audit-history.json"
CHECKPOINTS_PATH = RUNTIME_PATH / "campaign-checkpoints.json"
REVIEW_DECISIONS_PATH = RUNTIME_PATH / "review-decisions.json"
ANALYTICS_REFRESH_PATH = RUNTIME_PATH / "analytics-refresh.json"
CLI_WORKER_ID = "creativeos-cli"


class CampaignRuntimeCommandError(ValueError):
    """Reject unsafe or incomplete CLI runtime execution."""


@app.command("create")
def create_campaign(
    name: str = typer.Argument(..., help="Campaign or release name."),
    artist: str | None = typer.Option(None, "--artist", help="Override the configured artist."),
) -> None:
    """Create a complete campaign workspace."""
    try:
        project = Project.discover()
        path: Path = CampaignService(project).create(name, artist=artist)
    except (ConfigurationError, FileExistsError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]Created campaign:[/bold green] {path}")


@app.command("generate")
def generate_campaign(
    name: str = typer.Argument(..., help="Campaign or release name."),
    force: bool = typer.Option(False, "--force", help="Replace existing campaign content."),
) -> None:
    """Generate marketing assets for an existing campaign."""
    try:
        project = Project.discover()
        provider = AIManager(project.config.ai).default()
        paths = CampaignGeneratorService(project, provider).generate(name, force=force)
    except (ConfigurationError, FileExistsError, FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Generated {len(paths)} campaign assets[/bold green] using {provider.name}."
    )
    for path in paths:
        console.print(f"- {path.relative_to(project.root)}")


@app.command("status")
def campaign_status(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
) -> None:
    """Display a persisted campaign run without advancing it."""
    try:
        project = Project.discover()
        run = JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH).load(campaign_id)
    except (ConfigurationError, CampaignRunStateError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    evidence = (
        "\n".join(
            f"{item.kind}: {item.reference_id} (recorded by {item.recorded_by})"
            for item in run.evidence
        )
        or "None recorded"
    )
    table = Table(
        title="Campaign Runtime Status",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_row("Campaign ID", run.campaign_id)
    table.add_row("Work ID", run.work_id)
    table.add_row("Work", run.plan.work_name)
    table.add_row("Stage", run.stage)
    table.add_row("Evidence", evidence)
    table.add_row("Next requirement", run.requires_action)
    console.print(table)


@app.command("run")
def campaign_run(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
) -> None:
    """Advance at most one safe campaign runtime action."""
    try:
        project = Project.discover()
        now = datetime.now(UTC)
        run_store = JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH)
        queue_store = JsonExecutionQueueStore(project.root / QUEUE_PATH)
        history_store = JsonAuditHistoryStore(project.root / AUDIT_HISTORY_PATH)
        checkpoint_store = JsonRuntimeCheckpointStore(project.root / CHECKPOINTS_PATH)

        run = run_store.load(campaign_id)
        queue_state = queue_store.load()
        history = history_store.load()
        due = CampaignQueueService().ready(queue_state.queue, now=now)
        if run.stage == "in-production" and any(job.request.work_id == run.work_id for job in due):
            raise CampaignRuntimeCommandError(
                "provider execution requires explicit CLI provider configuration"
            )

        outcome = CheckpointedCampaignRuntime().advance(
            campaign_id,
            run_store,
            checkpoint_store,
            queue_state.queue,
            history,
            (),
            worker_id=CLI_WORKER_ID,
            now=now,
        )
        if outcome.uncertain:
            raise CampaignRuntimeCommandError(
                "runtime action is uncertain; reconcile it before retrying"
            )

        if outcome.result is None:
            checkpoint = outcome.checkpoint
            if checkpoint is None or checkpoint.status != "completed":
                raise CampaignRuntimeCommandError("runtime produced no reportable outcome")
            action = checkpoint.result_action or "completed"
            stage = checkpoint.resulting_stage or run.stage
            request_id = checkpoint.request_id
            paused = action.startswith("awaiting-") or action in {
                "execution-failed",
                "completed",
            }
        else:
            result = outcome.result
            action = result.action
            stage = result.run.stage
            request_id = result.request_id
            paused = result.paused
            if result.queue != queue_state.queue:
                queue_store.save(PersistentQueue(queue=result.queue, leases=queue_state.leases))
            if result.history != history:
                history_store.save(result.history)
    except (
        ConfigurationError,
        CampaignRunStateError,
        QueueStateError,
        AuditHistoryStateError,
        RuntimeCheckpointError,
        CampaignRuntimeCommandError,
        PermissionError,
        ValueError,
    ) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title="Campaign Runtime Action",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_row("Campaign ID", campaign_id)
    table.add_row("Stage", stage)
    table.add_row("Action", action)
    table.add_row("Request ID", request_id or "None")
    table.add_row("Paused", "Yes" if paused else "No")
    console.print(table)


@app.command("review")
def campaign_review(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
    review_id: str | None = typer.Option(None, "--review-id", help="Exact pending review ID."),
    decision: str | None = typer.Option(None, "--decision", help="Decision for one review item."),
    decided_by: str | None = typer.Option(
        None,
        "--decided-by",
        help="Operator identity required when recording a decision.",
    ),
    reason: str | None = typer.Option(
        None,
        "--reason",
        help="Reason required for negative or not-completed decisions.",
    ),
) -> None:
    """List pending reviews or record exactly one attributable decision."""
    try:
        project = Project.discover()
        now = datetime.now(UTC)
        run = JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH).load(campaign_id)
        checkpoint_store = JsonRuntimeCheckpointStore(project.root / CHECKPOINTS_PATH)
        decision_store = JsonReviewDecisionStore(project.root / REVIEW_DECISIONS_PATH)
        history_store = JsonAuditHistoryStore(project.root / AUDIT_HISTORY_PATH)

        inbox = HumanReviewInboxService().build(
            (run,),
            checkpoints=tuple(
                item for item in checkpoint_store.load() if item.campaign_id == campaign_id
            ),
        )
        recorded = {
            item.review_id: item
            for item in decision_store.load()
            if item.campaign_id == campaign_id
        }
        pending = ReviewInbox(
            items=tuple(item for item in inbox.items if item.review_id not in recorded)
        )

        supplied = (review_id is not None, decision is not None, decided_by is not None)
        if any(supplied) and not all(supplied):
            raise CampaignRuntimeCommandError(
                "--review-id, --decision, and --decided-by must be supplied together"
            )

        stored = None
        if all(supplied):
            selected = next(
                (item for item in inbox.items if item.review_id == review_id),
                None,
            )
            if selected is None:
                raise CampaignRuntimeCommandError(f"unknown review_id: {review_id}")
            selected_inbox = ReviewInbox(items=(selected,))
            stored = decision_store.record(
                selected_inbox,
                ReviewDecision(
                    review_id=review_id or "",
                    decision=decision or "",
                    decided_by=decided_by or "",
                    reason=reason,
                ),
                decided_at=now,
            )
            history = history_store.load()
            event_id = f"review-decision:{stored.review_id}"
            if not any(event.event_id == event_id for event in history.events):
                history = AuditHistoryService().record(
                    history,
                    AuditEvent(
                        event_id=event_id,
                        occurred_at=stored.decided_at,
                        category="approval",
                        action=stored.decision,
                        subject_id=stored.subject_id,
                        actor=stored.decided_by,
                        reference_id=stored.review_id,
                        detail=stored.reason,
                    ),
                )
                history_store.save(history)
            pending = ReviewInbox(
                items=tuple(item for item in pending.items if item.review_id != stored.review_id)
            )
    except (
        ConfigurationError,
        CampaignRunStateError,
        RuntimeCheckpointError,
        ReviewDecisionStateError,
        AuditHistoryStateError,
        CampaignRuntimeCommandError,
        PermissionError,
        ValueError,
    ) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if stored is not None:
        console.print(f"[bold green]Recorded {stored.decision}:[/bold green] {stored.review_id}")

    table = Table(title="Campaign Human Reviews", pad_edge=False)
    table.add_column("Review ID")
    table.add_column("Kind")
    table.add_column("Title")
    table.add_column("Detail")
    table.add_column("Allowed decisions")
    for item in pending.items:
        table.add_row(
            item.review_id,
            item.kind,
            item.title,
            item.detail,
            ", ".join(item.allowed_decisions),
        )
    console.print(table)
    if not pending.items:
        console.print("No pending reviews.")


@app.command("resume")
def campaign_resume(
    campaign_id: str = typer.Argument(..., help="Persisted campaign runtime ID."),
) -> None:
    """Reconcile one uncertain campaign action from a durable human decision."""
    try:
        project = Project.discover()
        now = datetime.now(UTC)
        run = JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH).load(campaign_id)
        checkpoint_store = JsonRuntimeCheckpointStore(project.root / CHECKPOINTS_PATH)
        decision_store = JsonReviewDecisionStore(project.root / REVIEW_DECISIONS_PATH)
        queue_state = JsonExecutionQueueStore(project.root / QUEUE_PATH).load()
        history_store = JsonAuditHistoryStore(project.root / AUDIT_HISTORY_PATH)
        history = history_store.load()

        decisions = tuple(
            item
            for item in decision_store.load()
            if item.campaign_id == campaign_id and item.kind == "uncertain-action"
        )
        if not decisions:
            raise CampaignRuntimeCommandError(
                "no recorded uncertain-action decision exists for this campaign"
            )

        checkpoints = tuple(
            item for item in checkpoint_store.load() if item.campaign_id == campaign_id
        )
        selected = next(
            (
                (checkpoint, decision)
                for decision in decisions
                for checkpoint in checkpoints
                if checkpoint.checkpoint_id == decision.subject_id
            ),
            None,
        )
        if selected is None:
            raise CampaignRuntimeCommandError(
                "recorded decision does not match a campaign checkpoint"
            )
        checkpoint, decision = selected
        event_id = f"checkpoint-reconciliation:{decision.review_id}"
        existing_event = next(
            (event for event in history.events if event.event_id == event_id),
            None,
        )
        if existing_event is not None:
            action = existing_event.action
            replayed = True
        else:
            if checkpoint.status != "uncertain":
                raise CampaignRuntimeCommandError(
                    "matching checkpoint is not awaiting reconciliation"
                )

            result_action = None
            request_id = None
            resulting_stage = None
            outcome_reference = None
            if decision.decision == "confirm-completed":
                if not checkpoint.action_key.startswith("execution:"):
                    raise CampaignRuntimeCommandError(
                        "confirm-completed requires a verifiable persisted provider outcome"
                    )
                request_id = checkpoint.action_key.removeprefix("execution:")
                job = next(
                    (
                        item
                        for item in queue_state.queue.jobs
                        if item.request.request_id == request_id
                    ),
                    None,
                )
                if job is None or job.status != "completed" or job.receipt is None:
                    raise CampaignRuntimeCommandError(
                        "confirm-completed requires a matching completed queue receipt"
                    )
                result_action = "execution-completed"
                resulting_stage = run.stage
                outcome_reference = job.receipt.external_id

            resolved = checkpoint_store.reconcile(
                checkpoint,
                decision=decision.decision,
                now=now,
                result_action=result_action,
                request_id=request_id,
                resulting_stage=resulting_stage,
            )
            history = AuditHistoryService().record(
                history,
                AuditEvent(
                    event_id=event_id,
                    occurred_at=now,
                    category="execution",
                    action=decision.decision,
                    subject_id=checkpoint.checkpoint_id,
                    actor=decision.decided_by,
                    reference_id=outcome_reference or decision.review_id,
                    detail=decision.reason,
                ),
            )
            history_store.save(history)
            action = resolved.result_action or decision.decision
            replayed = False
    except (
        ConfigurationError,
        CampaignRunStateError,
        QueueStateError,
        ReviewDecisionStateError,
        AuditHistoryStateError,
        RuntimeCheckpointError,
        CampaignRuntimeCommandError,
        PermissionError,
        ValueError,
    ) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(
        title="Campaign Runtime Resume",
        show_header=False,
        box=None,
        pad_edge=False,
    )
    table.add_row("Campaign ID", campaign_id)
    table.add_row("Checkpoint", checkpoint.checkpoint_id)
    table.add_row("Decision", decision.decision)
    table.add_row("Action", action)
    table.add_row("Replayed", "Yes" if replayed else "No")
    console.print(table)


@app.command("dashboard")
def campaign_dashboard() -> None:
    """Display a read-only overview of every persisted campaign runtime."""
    try:
        project = Project.discover()
        runs = JsonCampaignRunStore(project.root / CAMPAIGN_RUNS_PATH).load_all()

        queue_path = project.root / QUEUE_PATH
        queue_state = (
            JsonExecutionQueueStore(queue_path).load() if queue_path.exists() else PersistentQueue()
        )
        audit_path = project.root / AUDIT_HISTORY_PATH
        history = (
            JsonAuditHistoryStore(audit_path).load() if audit_path.exists() else AuditHistory()
        )
        checkpoint_path = project.root / CHECKPOINTS_PATH
        checkpoints = (
            JsonRuntimeCheckpointStore(checkpoint_path).load() if checkpoint_path.exists() else ()
        )
        decision_path = project.root / REVIEW_DECISIONS_PATH
        decisions = JsonReviewDecisionStore(decision_path).load() if decision_path.exists() else ()
        analytics_path = project.root / ANALYTICS_REFRESH_PATH
        analytics = (
            JsonAnalyticsRefreshStore(analytics_path).load() if analytics_path.exists() else ()
        )

        dashboard = OperationsDashboardService().build(
            runs,
            queue_state.queue,
            history,
        )
        inbox = HumanReviewInboxService().build(
            runs,
            checkpoints=checkpoints,
        )
        decided_ids = {item.review_id for item in decisions}
        pending_by_campaign: dict[str, int] = {}
        for item in inbox.items:
            if item.review_id not in decided_ids:
                pending_by_campaign[item.campaign_id] = (
                    pending_by_campaign.get(item.campaign_id, 0) + 1
                )

        uncertain_by_campaign = {
            item.campaign_id: item for item in checkpoints if item.status == "uncertain"
        }
        decided_subjects = {
            item.subject_id for item in decisions if item.kind == "uncertain-action"
        }
    except (
        ConfigurationError,
        CampaignRunStateError,
        QueueStateError,
        AuditHistoryStateError,
        RuntimeCheckpointError,
        ReviewDecisionStateError,
        ScheduledAnalyticsRefreshError,
        ValueError,
    ) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    campaigns = Table(title="Campaign Operations", pad_edge=False)
    campaigns.add_column("Campaign")
    campaigns.add_column("Stage")
    campaigns.add_column("Next requirement")
    campaigns.add_column("Pending reviews")
    campaigns.add_column("Recommended command")
    for item in dashboard.campaigns:
        uncertain = uncertain_by_campaign.get(item.campaign_id)
        if uncertain is not None:
            command = (
                f"creativeos campaign resume {item.campaign_id}"
                if uncertain.checkpoint_id in decided_subjects
                else f"creativeos campaign review {item.campaign_id}"
            )
        elif item.stage == "completed":
            command = f"creativeos campaign status {item.campaign_id}"
        else:
            command = f"creativeos campaign run {item.campaign_id}"
        campaigns.add_row(
            item.campaign_id,
            item.stage,
            item.requires_action,
            str(pending_by_campaign.get(item.campaign_id, 0)),
            command,
        )
    console.print(campaigns)
    if not dashboard.campaigns:
        console.print("No persisted campaign runs.")

    queue = Table(title="Execution Queue", pad_edge=False)
    queue.add_column("Status")
    queue.add_column("Count")
    for status, count in dashboard.queue_status_counts:
        queue.add_row(status, str(count))
    console.print(queue)
    if not dashboard.queue_status_counts:
        console.print("Queue is empty.")
    for job in dashboard.failed_jobs:
        console.print(
            f"[bold red]Failed:[/bold red] {job.request_id} "
            f"({job.provider}, {job.asset_id}) — {job.reason}"
        )

    analytics_table = Table(title="Analytics Refresh", pad_edge=False)
    analytics_table.add_column("Status")
    analytics_table.add_column("Count")
    analytics_counts: dict[str, int] = {}
    for attempt in analytics:
        analytics_counts[attempt.status] = analytics_counts.get(attempt.status, 0) + 1
    for status, count in sorted(analytics_counts.items()):
        analytics_table.add_row(status, str(count))
    console.print(analytics_table)
    if not analytics:
        console.print("Analytics refresh is not configured.")
    else:
        latest = max(
            analytics,
            key=lambda item: (item.started_at, item.attempt_id),
        )
        detail = latest.failure_reason or (
            f"{latest.record_count} records"
            if latest.record_count is not None
            else "manual reconciliation required"
            if latest.status == "uncertain"
            else "in progress"
        )
        console.print(
            f"Latest: {latest.schedule_id} — {latest.status} "
            f"({latest.started_at.isoformat()}; {detail})"
        )

    events = Table(title="Recent Audit Activity", pad_edge=False)
    events.add_column("Occurred")
    events.add_column("Category")
    events.add_column("Action")
    events.add_column("Subject")
    for event in dashboard.recent_events:
        events.add_row(
            event.occurred_at.isoformat(),
            event.category,
            event.action,
            event.subject_id,
        )
    console.print(events)
    if not dashboard.recent_events:
        console.print("No audit activity recorded.")
