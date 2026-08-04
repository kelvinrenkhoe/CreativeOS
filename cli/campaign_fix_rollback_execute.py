"""Campaign fix rollback execution CLI command."""

from pathlib import Path

import typer
from rich.console import Console

from core.config import ConfigurationError
from core.project import Project
from renderers.campaign_fix_rollback_execution import (
    CampaignFixRollbackExecutionRenderer,
)
from services.campaign_fix_receipts import (
    CampaignFixReceiptError,
    JsonCampaignFixReceiptStore,
)
from services.campaign_fix_rollback import CampaignFixRollbackPlanner
from services.campaign_fix_rollback_executor import CampaignFixRollbackExecutor

console = Console()
RECEIPTS_PATH = Path(".creativeos") / "campaign-fix-receipts"


def rollback_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview rollback actions without changing the workspace.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Execute without an interactive confirmation prompt.",
    ),
) -> None:
    """Execute the latest safe campaign fix rollback plan."""
    try:
        project = Project.discover()
        receipt = JsonCampaignFixReceiptStore(project.root / RECEIPTS_PATH).load(campaign_name)
        plan = CampaignFixRollbackPlanner().plan(receipt)

        if not dry_run and not yes:
            confirmed = typer.confirm(
                f'Rollback safe fixes for "{campaign_name}"?',
                default=False,
            )
            if not confirmed:
                console.print("Rollback cancelled. Nothing was changed.")
                raise typer.Exit(code=0)

        report = CampaignFixRollbackExecutor().execute(
            project.root,
            plan,
            dry_run=dry_run,
        )
    except typer.Exit:
        raise
    except (ConfigurationError, CampaignFixReceiptError, OSError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignFixRollbackExecutionRenderer().render(report))
