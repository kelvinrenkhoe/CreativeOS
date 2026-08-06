"""Tests for specific marketing asset classification."""

from dataclasses import FrozenInstanceError

import pytest

from models.asset_intelligence import (
    AssetIntelligenceError,
    AssetKind,
    AssetType,
    CreativeAsset,
)
from services.asset_registry import AssetIntelligenceRegistry


def make_asset(
    asset_id: str,
    *,
    asset_kind: AssetKind = AssetKind.GENERIC,
) -> CreativeAsset:
    return CreativeAsset(
        asset_id=asset_id,
        campaign_id="no-lose-guard",
        project_id="no-lose-guard",
        asset_type=AssetType.VIDEO,
        asset_kind=asset_kind,
        concept="Stay focused through distraction",
        hook="Do not lose guard",
        call_to_action="Listen on release day",
        platform="instagram",
    )


def test_asset_kind_defines_modern_marketing_deliverables() -> None:
    assert AssetKind.VIDEO_CONCEPT.value == "video_concept"
    assert AssetKind.STORYBOARD.value == "storyboard"
    assert AssetKind.SHOT_LIST.value == "shot_list"
    assert AssetKind.SPOTIFY_CANVAS.value == "spotify_canvas"
    assert AssetKind.CONTENT_CALENDAR.value == "content_calendar"


def test_existing_asset_construction_defaults_to_generic_kind() -> None:
    asset = CreativeAsset(
        asset_id="asset-1",
        campaign_id="campaign-1",
        project_id="project-1",
        asset_type=AssetType.CAPTION,
        concept="Release announcement",
        hook="The wait is over",
        call_to_action="Listen now",
        platform="instagram",
    )

    assert asset.asset_kind is AssetKind.GENERIC


def test_creative_asset_remains_immutable() -> None:
    asset = make_asset("asset-1", asset_kind=AssetKind.VIDEO_CONCEPT)

    with pytest.raises(FrozenInstanceError):
        asset.asset_kind = AssetKind.STORYBOARD  # type: ignore[misc]


def test_creative_asset_rejects_untyped_asset_kind() -> None:
    with pytest.raises(AssetIntelligenceError, match="asset_kind must be an AssetKind"):
        CreativeAsset(
            asset_id="asset-1",
            campaign_id="campaign-1",
            project_id="project-1",
            asset_type=AssetType.VIDEO,
            asset_kind="video_concept",  # type: ignore[arg-type]
            concept="Release teaser",
            hook="Watch this",
            call_to_action="Follow",
            platform="tiktok",
        )


def test_registry_queries_assets_by_specific_kind() -> None:
    video = make_asset("video", asset_kind=AssetKind.VIDEO_CONCEPT)
    storyboard = make_asset("storyboard", asset_kind=AssetKind.STORYBOARD)
    registry = AssetIntelligenceRegistry((video, storyboard))

    assert registry.query(asset_kind=AssetKind.VIDEO_CONCEPT) == (video,)
    assert registry.query(asset_kind=AssetKind.STORYBOARD) == (storyboard,)


def test_asset_kind_contributes_to_similarity_fingerprint() -> None:
    video = make_asset("video", asset_kind=AssetKind.VIDEO_CONCEPT)
    storyboard = make_asset("storyboard", asset_kind=AssetKind.STORYBOARD)

    assert video.fingerprint != storyboard.fingerprint
    assert "video" in video.fingerprint_tokens
    assert "concept" in video.fingerprint_tokens
    assert "storyboard" in storyboard.fingerprint_tokens
