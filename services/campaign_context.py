"""Campaign discovery and loading beneath organization projects."""

from pathlib import Path

import yaml

from models.campaign_context import CampaignContext, CampaignContextError
from services.project_context import ProjectContextService

CAMPAIGNS_DIRECTORY = "campaigns"
CAMPAIGN_FILENAME = "campaign.yaml"


class CampaignContextLoadError(Exception):
    """Raised when a project campaign cannot be safely loaded."""


class CampaignContextService:
    """Discover and load campaigns scoped to one organization project."""

    def __init__(self, repository_root: Path, organization_id: str, project_id: str) -> None:
        self.project_service = ProjectContextService(repository_root, organization_id)
        self.organization = self.project_service.organization
        self.project = self.project_service.load(project_id)
        self.project_root = self.project_service.project_path(project_id)
        self.campaigns_root = self.project_root / CAMPAIGNS_DIRECTORY

    def list(self) -> tuple[CampaignContext, ...]:
        """Return valid campaigns in stable identifier order."""
        if not self.campaigns_root.is_dir():
            return ()

        campaigns: list[CampaignContext] = []
        entries = self.campaigns_root.iterdir()
        directories = sorted(path for path in entries if path.is_dir())
        for directory in directories:
            config_path = directory / CAMPAIGN_FILENAME
            if config_path.is_file():
                campaigns.append(self._load_file(config_path, expected_id=directory.name))
        return tuple(campaigns)

    def load(self, campaign_id: str) -> CampaignContext:
        """Load one campaign by validated identifier."""
        try:
            requested = CampaignContext(
                campaign_id=campaign_id,
                name="validation-placeholder",
            ).campaign_id
        except CampaignContextError as exc:
            raise CampaignContextLoadError(str(exc)) from exc

        config_path = self.campaigns_root / requested / CAMPAIGN_FILENAME
        if not config_path.is_file():
            project_id = self.project.project_id
            raise CampaignContextLoadError(
                f"unknown campaign {requested!r} for project {project_id!r}"
            )
        return self._load_file(config_path, expected_id=requested)

    def campaign_path(self, campaign_id: str) -> Path:
        """Return the safe directory for one existing project campaign."""
        campaign = self.load(campaign_id)
        path = (self.campaigns_root / campaign.campaign_id).resolve()
        if path.parent != self.campaigns_root.resolve():
            raise CampaignContextLoadError(
                "campaign path escaped the organization project campaigns directory"
            )
        return path

    def _load_file(self, config_path: Path, *, expected_id: str) -> CampaignContext:
        try:
            with config_path.open("r", encoding="utf-8") as file:
                raw = yaml.safe_load(file)
        except OSError as exc:
            raise CampaignContextLoadError(f"unable to read {config_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise CampaignContextLoadError(f"invalid YAML in {config_path}: {exc}") from exc

        try:
            campaign = CampaignContext.from_dict(raw)
        except CampaignContextError as exc:
            raise CampaignContextLoadError(f"invalid campaign configuration: {exc}") from exc

        if campaign.campaign_id != expected_id:
            raise CampaignContextLoadError(
                f"campaign id {campaign.campaign_id!r} does not match directory {expected_id!r}"
            )
        return campaign
