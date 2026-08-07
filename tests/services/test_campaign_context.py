from pathlib import Path

import pytest

from models.campaign_context import CampaignContext, CampaignContextError
from services.campaign_context import CampaignContextLoadError, CampaignContextService


def _write_campaign(root: Path, organization: str, project: str, campaign: str) -> None:
    organization_root = root / "organizations" / organization
    organization_root.mkdir(parents=True, exist_ok=True)
    (organization_root / "organization.yaml").write_text(
        f"id: {organization}\nname: {organization.title()}\n",
        encoding="utf-8",
    )
    project_root = organization_root / "projects" / project
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "project.yaml").write_text(
        f"id: {project}\nname: {project.title()}\n",
        encoding="utf-8",
    )
    campaign_root = project_root / "campaigns" / campaign
    campaign_root.mkdir(parents=True, exist_ok=True)
    (campaign_root / "campaign.yaml").write_text(
        f"id: {campaign}\nname: {campaign.title()}\nstatus: active\n",
        encoding="utf-8",
    )


def test_campaign_context_normalizes_identifiers() -> None:
    campaign = CampaignContext(
        campaign_id="Launch",
        name=" Launch Campaign ",
        campaign_type="Music Release",
        status="In Progress",
        channels=("Instagram", "TikTok"),
    )

    assert campaign.campaign_id == "launch"
    assert campaign.campaign_type == "music-release"
    assert campaign.status == "in-progress"
    assert campaign.channels == ("instagram", "tiktok")


def test_campaign_context_rejects_invalid_date_range() -> None:
    with pytest.raises(CampaignContextError, match="end_date cannot be before start_date"):
        CampaignContext.from_dict(
            {
                "id": "launch",
                "name": "Launch",
                "start_date": "2026-09-01",
                "end_date": "2026-08-01",
            }
        )


def test_service_lists_only_selected_project_campaigns(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    _write_campaign(tmp_path, "kre", "other-project", "other-launch")

    service = CampaignContextService(tmp_path, "kre", "no-lose-guard")

    assert [campaign.campaign_id for campaign in service.list()] == ["launch"]


def test_service_loads_campaign_and_returns_safe_path(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    service = CampaignContextService(tmp_path, "kre", "no-lose-guard")

    campaign = service.load("launch")

    assert campaign.name == "Launch"
    assert (
        service.campaign_path("launch")
        == (
            tmp_path
            / "organizations"
            / "kre"
            / "projects"
            / "no-lose-guard"
            / "campaigns"
            / "launch"
        ).resolve()
    )


def test_service_rejects_campaign_path_traversal(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    service = CampaignContextService(tmp_path, "kre", "no-lose-guard")

    with pytest.raises(CampaignContextLoadError):
        service.load("../../secrets")


def test_service_rejects_directory_configuration_id_mismatch(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "kre", "no-lose-guard", "launch")
    config_path = (
        tmp_path
        / "organizations"
        / "kre"
        / "projects"
        / "no-lose-guard"
        / "campaigns"
        / "launch"
        / "campaign.yaml"
    )
    config_path.write_text("id: wrong-id\nname: Launch\n", encoding="utf-8")
    service = CampaignContextService(tmp_path, "kre", "no-lose-guard")

    with pytest.raises(CampaignContextLoadError, match="does not match directory"):
        service.load("launch")
