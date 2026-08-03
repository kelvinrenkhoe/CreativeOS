"""Tests for campaign readiness diagnosis."""

from pathlib import Path

import yaml

from core.project import Project
from orchestrator import (
    CampaignRuntimePreset,
    CampaignRuntimePresetRegistry,
    RuntimeStage,
)
from services.campaign_doctor import CampaignDoctorService


def _project(tmp_path: Path) -> Project:
    config = {
        "version": 1,
        "workspace": {
            "name": "Kelvin Rankie Universe",
        },
        "artist": {
            "name": "Kelvin Rankie",
            "genre": "Afrobeats",
            "country": "United Kingdom",
        },
        "repository": {
            "songs": "songs",
            "campaigns": "campaigns",
            "books": "books",
            "templates": "templates",
            "assets": "assets",
            "knowledge": "knowledge",
            "media": "media",
        },
        "releases": {
            "current": "",
            "upcoming": "No Lose Guard",
        },
        "campaigns": {
            "active": ["no-lose-guard"],
        },
    }

    (tmp_path / "creativeos.yaml").write_text(
        yaml.safe_dump(config),
        encoding="utf-8",
    )

    for directory in config["repository"].values():
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)

    return Project.discover(tmp_path)


def _registry() -> CampaignRuntimePresetRegistry:
    registry = CampaignRuntimePresetRegistry()
    registry.register(
        CampaignRuntimePreset(
            name="music-release",
            description="Music release test preset.",
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


def _write_campaign(
    project: Project,
    *,
    release_date: str | None = "2026-09-01",
) -> Path:
    path = project.campaigns_path / "no-lose-guard"
    path.mkdir(parents=True)

    manifest = {
        "name": "No Lose Guard",
        "artist": "Kelvin Rankie",
        "release_date": release_date,
        "platforms": ["spotify", "instagram"],
        "goals": {"spotify_streams": 100000},
    }

    (path / "campaign.yaml").write_text(
        yaml.safe_dump(manifest),
        encoding="utf-8",
    )

    return path


def test_complete_required_campaign_checks_are_healthy(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_campaign(project)

    report = CampaignDoctorService(project, _registry()).diagnose(
        "No Lose Guard",
        context={"campaign": "No Lose Guard"},
    )

    assert report.healthy is True
    assert report.failed_count == 0
    assert report.warning_count > 0


def test_missing_release_date_is_required_failure(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_campaign(project, release_date=None)

    report = CampaignDoctorService(project, _registry()).diagnose(
        "No Lose Guard",
        context={"campaign": "No Lose Guard"},
    )

    release_check = next(check for check in report.checks if check.name == "Release date")

    assert release_check.failed is True
    assert report.healthy is False


def test_missing_optional_assets_are_warnings(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_campaign(project)

    report = CampaignDoctorService(project, _registry()).diagnose(
        "No Lose Guard",
        context={"campaign": "No Lose Guard"},
    )

    artwork = next(check for check in report.checks if check.name == "Artwork")

    assert artwork.warning is True
    assert artwork.failed is False


def test_unknown_campaign_is_unhealthy(tmp_path: Path) -> None:
    project = _project(tmp_path)

    report = CampaignDoctorService(project, _registry()).diagnose(
        "Missing Campaign",
        context={"campaign": "Missing Campaign"},
    )

    assert report.healthy is False
    assert report.failed_count >= 1


def test_unknown_runtime_preset_is_failure(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_campaign(project)

    report = CampaignDoctorService(project, _registry()).diagnose(
        "No Lose Guard",
        preset_name="missing",
        context={"campaign": "No Lose Guard"},
    )

    preset = next(check for check in report.checks if check.name == "Runtime preset")

    assert preset.failed is True


def test_missing_required_runtime_context_is_failure(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_campaign(project)

    report = CampaignDoctorService(project, _registry()).diagnose(
        "No Lose Guard",
        context={},
    )

    context_check = next(check for check in report.checks if check.name == "Context: campaign")

    assert context_check.failed is True
    assert report.healthy is False


def test_diagnosis_does_not_modify_campaign_files(tmp_path: Path) -> None:
    project = _project(tmp_path)
    campaign_path = _write_campaign(project)

    before = {
        path.relative_to(campaign_path): path.read_bytes()
        for path in campaign_path.rglob("*")
        if path.is_file()
    }

    service = CampaignDoctorService(project, _registry())
    first = service.diagnose(
        "No Lose Guard",
        context={"campaign": "No Lose Guard"},
    )
    second = service.diagnose(
        "No Lose Guard",
        context={"campaign": "No Lose Guard"},
    )

    after = {
        path.relative_to(campaign_path): path.read_bytes()
        for path in campaign_path.rglob("*")
        if path.is_file()
    }

    assert first == second
    assert before == after
