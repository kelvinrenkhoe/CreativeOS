"""Safe campaign fix CLI command."""

from pathlib import Path

import typer
from rich.console import Console

from core.config import ConfigurationError
from core.project import Project
from orchestrator import CampaignRuntimePreset, CampaignRuntimePresetRegistry, RuntimeStage
from renderers.campaign_fix_execution import CampaignFixExecutionRenderer
from services.campaign_autofix import CampaignAutoFixPlanner
from services.campaign_doctor import CampaignDoctorService
from services.campaign_fix_executor import CampaignFixExecutor
from services.campaign_fix_receipts import JsonCampaignFixReceiptStore
from services.campaign_recommendations import CampaignRecommendationsService

console = Console()
RECEIPTS_PATH = Path(".creativeos") / "campaign-fix-receipts"


def _campaign_doctor_registry() -> CampaignRuntimePresetRegistry:
    """Return runtime preset metadata used by campaign fix checks."""
    registry = CampaignRuntimePresetRegistry()
    registry.register(
        CampaignRuntimePreset(
            name="music-release",
            description="Validate a music-release campaign before fixing it.",
            required_context_keys=("campaign",),
            stages=(
                RuntimeStage(
                    "brief",
                    lambda campaign: campaign,
                    ("campaign",),
                    "brief",
                ),
            ),
        )
    )
    return registry


def fix_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Apply only safe deterministic campaign fixes."""
    try:
        project = Project.discover()
        doctor_report = CampaignDoctorService(
            project,
            _campaign_doctor_registry(),
        ).diagnose(
            campaign_name,
            context={"campaign": campaign_name},
        )
        recommendations = CampaignRecommendationsService().recommend(
            campaign_name,
            doctor_report,
        )
        plan = CampaignAutoFixPlanner().plan(recommendations)
        execution = CampaignFixExecutor().execute(project.root, plan)
        JsonCampaignFixReceiptStore(
            project.root / RECEIPTS_PATH
        ).save(execution)
    except (ConfigurationError, OSError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignFixExecutionRenderer().render(execution))
