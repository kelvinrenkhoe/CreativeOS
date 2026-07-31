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
from services.operations_dashboard import AuditEvent, AuditHistoryService
from services.persistent_queue import (
    JsonExecutionQueueStore,
    PersistentQueue,
    QueueStateError,
)
from services.review_decision_store import (
    JsonReviewDecisionStore,
    ReviewDecisionStateError,
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
