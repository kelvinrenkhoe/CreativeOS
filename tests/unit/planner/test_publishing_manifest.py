"""Tests for deterministic package-backed publishing manifests."""

import json

import pytest

from models.campaign_package import (
    CampaignPackage,
    PackageAsset,
    PackageManifest,
    PackageMediaType,
    PackageMetadata,
)
from models.publishing import (
    ApprovalStatus,
    PublishingError,
    PublishingFormat,
    PublishingPlatform,
    PublishingSlot,
)
from planner.publishing_manifest import PublishingManifestPlanner


def _package() -> CampaignPackage:
    assets = (
        PackageAsset("copy/captions.md", PackageMediaType.MARKDOWN, "Captions"),
        PackageAsset("visuals/video_prompts.md", PackageMediaType.MARKDOWN, "Videos"),
    )
    paths = tuple(asset.path for asset in assets)
    return CampaignPackage(
        package_id="no-lose-guard-week-03",
        root_path="no-lose-guard/Week-03",
        metadata=PackageMetadata("1.0.0-alpha", 1, "nlg", "No Lose Guard", 3, "2026-08-02"),
        manifest=PackageManifest("no-lose-guard-week-03", "nlg", 3, paths),
        assets=assets,
    )


def _slots() -> tuple[PublishingSlot, ...]:
    return (
        PublishingSlot(
            slot_id="tuesday-tiktok",
            day=2,
            time="20:00",
            platform=PublishingPlatform.TIKTOK,
            content_format=PublishingFormat.SHORT,
            primary_asset_path="visuals/video_prompts.md",
            supporting_asset_paths=("copy/captions.md",),
            dependency_slot_ids=("monday-instagram",),
        ),
        PublishingSlot(
            slot_id="monday-instagram",
            day=1,
            time="18:00",
            platform=PublishingPlatform.INSTAGRAM,
            content_format=PublishingFormat.REEL,
            primary_asset_path="visuals/video_prompts.md",
            supporting_asset_paths=("copy/captions.md",),
            approval_status=ApprovalStatus.APPROVED,
        ),
    )


def test_planner_orders_slots_and_preserves_campaign_context() -> None:
    manifest = PublishingManifestPlanner().plan(_package(), _slots(), timezone="Europe/London")

    assert tuple(slot.slot_id for slot in manifest.slots) == (
        "monday-instagram",
        "tuesday-tiktok",
    )
    assert manifest.campaign_id == "nlg"
    assert manifest.campaign_week == 3
    assert manifest.timezone == "Europe/London"


def test_package_asset_is_stable_json() -> None:
    planner = PublishingManifestPlanner()
    manifest = planner.plan(_package(), _slots(), timezone="Europe/London")

    first = planner.package_asset(manifest)
    second = planner.package_asset(manifest)
    payload = json.loads(first.content)

    assert first == second
    assert first.path == "publishing/publishing_manifest.json"
    assert payload["slots"][0]["platform"] == "instagram"
    assert payload["slots"][1]["dependency_slot_ids"] == ["monday-instagram"]


def test_missing_package_asset_is_rejected() -> None:
    slot = PublishingSlot(
        slot_id="missing-video",
        day=1,
        time="18:00",
        platform=PublishingPlatform.INSTAGRAM,
        content_format=PublishingFormat.REEL,
        primary_asset_path="visuals/rendered-video.mp4",
    )

    with pytest.raises(PublishingError, match="references missing assets"):
        PublishingManifestPlanner().plan(_package(), (slot,), timezone="Europe/London")


def test_slot_rejects_invalid_time() -> None:
    with pytest.raises(PublishingError, match="valid 24-hour"):
        PublishingSlot(
            slot_id="bad-time",
            day=1,
            time="25:00",
            platform=PublishingPlatform.X,
            content_format=PublishingFormat.POST,
            primary_asset_path="copy/captions.md",
        )
