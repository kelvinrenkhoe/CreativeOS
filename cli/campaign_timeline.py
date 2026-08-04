"""Campaign release timeline CLI command."""

from dataclasses import fields
from datetime import date

import typer
import yaml
from rich.console import Console

from cli.campaign import app as campaign_app
from core.config import ConfigurationError
from core.project import Project
from models.campaign import CampaignManifest
from renderers.campaign_release_timeline import CampaignReleaseTimelineRenderer
from services.campaign import slugify
from services.campaign_release_timeline import CampaignReleaseTimelineService

console = Console()


def _load_manifest(project: Project, campaign_name: str) -> CampaignManifest:
    """Load and validate one campaign manifest without modifying it."""
    campaign_path = project.campaigns_path / slugify(campaign_name)
    manifest_path = campaign_path / "campaign.yaml"

    if not campaign_path.is_dir():
        raise ValueError(
            f'Campaign workspace not found for "{campaign_name}". '
            f'Run: creativeos campaign create "{campaign_name}"'
        )
    if not manifest_path.is_file():
        raise ValueError(f"Campaign manifest not found: {manifest_path}")

    try:
        loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid campaign manifest: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ValueError("Campaign manifest must contain a mapping")

    allowed_fields = {field.name for field in fields(CampaignManifest)}
    manifest_data = {key: value for key, value in loaded.items() if key in allowed_fields}
    try:
        return CampaignManifest(**manifest_data)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid campaign manifest: {exc}") from exc


def timeline_command(
    campaign_name: str = typer.Argument(..., help="Campaign or release name."),
) -> None:
    """Display the deterministic release timeline for a campaign."""
    try:
        project = Project.discover()
        manifest = _load_manifest(project, campaign_name)
        if not manifest.release_date:
            raise ValueError(
                f'Release date is not configured for "{campaign_name}". '
                "Add release_date to campaign.yaml using YYYY-MM-DD."
            )
        try:
            release_date = date.fromisoformat(manifest.release_date)
        except ValueError as exc:
            raise ValueError(
                f"Invalid release date: {manifest.release_date}; expected YYYY-MM-DD"
            ) from exc

        timeline = CampaignReleaseTimelineService().generate(release_date)
    except (ConfigurationError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(CampaignReleaseTimelineRenderer().render(campaign_name, timeline))


campaign_app.command("timeline")(timeline_command)
