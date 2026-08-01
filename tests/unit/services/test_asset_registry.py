"""Tests for deterministic creative asset intelligence."""

import pytest

from models.asset_intelligence import (
    AssetIntelligenceError,
    AssetStatus,
    AssetType,
    AssetUsage,
    CreativeAsset,
)
from services.asset_registry import AssetIntelligenceRegistry


def asset(asset_id: str, **overrides) -> CreativeAsset:
    values = {
        "asset_id": asset_id,
        "campaign_id": "no-lose-guard",
        "project_id": "no-lose-guard-song",
        "asset_type": AssetType.VIDEO,
        "concept": "A night-shift worker walks into sunrise after a difficult week.",
        "hook": "Every sacrifice counts.",
        "call_to_action": "Stream No Lose Guard.",
        "platform": "instagram",
        "campaign_week": 3,
        "tags": ("hope", "perseverance"),
        "descriptors": ("cinematic", "sunrise"),
    }
    values.update(overrides)
    return CreativeAsset(**values)


def test_fingerprint_is_deterministic_and_normalized() -> None:
    first = asset("clip-1", tags=("Hope", "Perseverance"))
    second = asset("clip-2", tags=("perseverance", "hope"))

    assert first.fingerprint == second.fingerprint
    assert first.fingerprint_tokens == second.fingerprint_tokens


def test_registry_rejects_duplicate_asset_ids() -> None:
    registry = AssetIntelligenceRegistry((asset("clip-1"),))

    with pytest.raises(AssetIntelligenceError, match="duplicate asset_id"):
        registry.register(asset("clip-1", concept="Another concept"))


def test_query_preserves_registration_order() -> None:
    first = asset("clip-1")
    second = asset(
        "caption-1",
        asset_type=AssetType.CAPTION,
        platform="facebook",
        status=AssetStatus.APPROVED,
    )
    third = asset("clip-2", usages=(AssetUsage("instagram", "advert", 4),))
    registry = AssetIntelligenceRegistry((first, second, third))

    assert registry.query(campaign_id="no-lose-guard") == (first, second, third)
    assert registry.query(asset_type=AssetType.VIDEO) == (first, third)
    assert registry.query(platform=" FACEBOOK ") == (second,)
    assert registry.query(status=AssetStatus.APPROVED) == (second,)
    assert registry.query(used=True) == (third,)


def test_detects_exact_and_near_duplicate_directions() -> None:
    original = asset("clip-1")
    exact = asset("clip-2")
    near = asset(
        "clip-3",
        concept="A tired night worker steps outside into a hopeful sunrise.",
        hook="Every sacrifice matters.",
    )
    registry = AssetIntelligenceRegistry((original, exact, near))

    exact_result = registry.similarity("clip-1", "clip-2")
    near_result = registry.similarity("clip-1", "clip-3")

    assert exact_result.exact_match
    assert exact_result.score == 1.0
    assert not near_result.exact_match
    assert 0 < near_result.score < 1


def test_similar_to_filters_by_campaign_and_threshold() -> None:
    original = asset("clip-1")
    another_campaign = asset("clip-2", campaign_id="carry-your-name")
    registry = AssetIntelligenceRegistry((original, another_campaign))
    proposal = asset("proposal")

    assert registry.excluded_asset_ids(
        proposal,
        threshold=1.0,
        campaign_id="no-lose-guard",
    ) == ("clip-1",)

    with pytest.raises(AssetIntelligenceError, match="threshold"):
        registry.similar_to(proposal, threshold=1.1)


def test_usage_and_required_metadata_validation() -> None:
    usage = AssetUsage(" tiktok ", " teaser ", 2)
    assert usage.platform == "tiktok"
    assert usage.purpose == "teaser"

    with pytest.raises(AssetIntelligenceError, match="campaign_week"):
        AssetUsage("tiktok", "teaser", 0)

    with pytest.raises(AssetIntelligenceError, match="concept"):
        asset("clip-1", concept=" ")

    with pytest.raises(AssetIntelligenceError, match="tags must be unique"):
        asset("clip-1", tags=("hope", "Hope"))
