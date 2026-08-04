"""Read-only campaign fix rollback plan CLI command."""

from pathlib import Path

import typer
from rich.console import Console

from core.config import ConfigurationError
from core.project import Project
from renderers.campaign_fix_rollback import CampaignFixRollbackRenderer
from services.campaign_fix_receipts import (
    CampaignFixReceiptError,
    JsonCampaignFixReceiptStore,
)
from services.campaign_fix_rollback import CampaignFixRollbackPlanner

console = Console()
RECEIPTS_PATH = Path(".creativeos") / "campaign-fix-receipts"


def rollback_plan_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Display a read-only rollback plan for the latest campaign fix."""
    try:
        project = Project.discover()
        receipt = JsonCampaignFixReceiptStore(
            project.root / RECEIPTS_PATH
        ).load(campaign_name)
        plan = CampaignFixRollbackPlanner().plan(receipt)
    except (ConfigurationError, CampaignFixReceiptError, OSError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignFixRollbackRenderer().render(plan))
