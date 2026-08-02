"""Tests for deterministic weekly creative package export."""

import json

import pytest

from exporters.package_exporter import PackageExporter
from models.campaign_package import PackageAsset, PackageError, PackageMediaType
from models.creative_brief import CreativeBrief


def _brief() -> CreativeBrief:
    return CreativeBrief(
        campaign_id="no-lose-guard",
        campaign_name="No Lose Guard",
        artist="Kelvin Rankie",
        objective="Build anticipation for the single.",
        audience="Independent Afrobeats listeners.",
        tone="Hopeful and determined.",
        platforms=("Instagram", "TikTok"),
        knowledge="Release campaign knowledge.",
        story_context="A story about resilience.",
        memory="Avoid repeated hooks.",
        completed_item_ids=(),
        ready_item_ids=("scene-1",),
        blocked_items=(),
        next_item_id="scene-1",
        next_reason="Review the first visual sequence.",
        recovery=None,
    )


def _assets() -> tuple[PackageAsset, ...]:
    return (
        PackageAsset(
            "strategy/storyboard.md",
            PackageMediaType.MARKDOWN,
            "# Storyboard",
        ),
        PackageAsset(
            "strategy/creative_brief.md",
            PackageMediaType.MARKDOWN,
            "# Creative Brief",
        ),
        PackageAsset(
            "copy/captions.md",
            PackageMediaType.MARKDOWN,
            "# Captions",
        ),
    )


def test_export_builds_stable_sorted_package() -> None:
    package = PackageExporter().export(
        _brief(),
        3,
        _assets(),
        creativeos_version="1.0.0-alpha",
        generated_at="2026-08-02T12:00:00Z",
    )

    assert package.package_id == "no-lose-guard-week-03"
    assert package.root_path == "no-lose-guard/Week-03"
    assert tuple(asset.path for asset in package.assets) == (
        "README.md",
        "copy/captions.md",
        "manifest.json",
        "metadata.json",
        "strategy/creative_brief.md",
        "strategy/storyboard.md",
    )
    assert package.manifest.asset_paths == tuple(asset.path for asset in package.assets)


def test_export_renders_readme_manifest_and_metadata() -> None:
    package = PackageExporter().export(
        _brief(),
        3,
        _assets(),
        creativeos_version="1.0.0-alpha",
        generated_at="2026-08-02T12:00:00Z",
    )

    readme = package.get("README.md").content
    manifest = json.loads(package.get("manifest.json").content)
    metadata = json.loads(package.get("metadata.json").content)

    assert "# No Lose Guard — Week 3" in readme
    assert "Review the first visual sequence." in readme
    assert manifest["package_id"] == "no-lose-guard-week-03"
    assert manifest["asset_paths"] == list(package.manifest.asset_paths)
    assert metadata == {
        "campaign_id": "no-lose-guard",
        "campaign_name": "No Lose Guard",
        "campaign_week": 3,
        "creativeos_version": "1.0.0-alpha",
        "generated_at": "2026-08-02T12:00:00Z",
        "schema_version": 1,
    }


def test_export_rejects_missing_required_assets() -> None:
    with pytest.raises(PackageError, match="strategy/storyboard.md"):
        PackageExporter().export(
            _brief(),
            1,
            (
                PackageAsset(
                    "strategy/creative_brief.md",
                    PackageMediaType.MARKDOWN,
                    "# Creative Brief",
                ),
            ),
            creativeos_version="1.0.0-alpha",
            generated_at="2026-08-02T12:00:00Z",
        )


def test_export_is_deterministic() -> None:
    exporter = PackageExporter()
    first = exporter.export(
        _brief(),
        2,
        _assets(),
        creativeos_version="1.0.0-alpha",
        generated_at="2026-08-02T12:00:00Z",
    )
    second = exporter.export(
        _brief(),
        2,
        tuple(reversed(_assets())),
        creativeos_version="1.0.0-alpha",
        generated_at="2026-08-02T12:00:00Z",
    )

    assert first == second
