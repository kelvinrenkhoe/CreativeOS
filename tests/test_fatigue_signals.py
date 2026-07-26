import pytest

from services.asset_intelligence import NoveltyAssessment
from services.campaign_measurement import CampaignMeasurementService
from services.fatigue_signals import (
    CreativeFatigueInput,
    FatigueSignalService,
)
from services.performance_ingestion import (
    PerformanceIngestionService,
    PerformanceRecord,
)


def measurement(campaign_id: str, value: float):
    record = PerformanceRecord(
        asset_id="poster",
        platform="instagram",
        external_id="post-1",
        metric="views",
        value=value,
        observed_at="2026-07-26T08:00:00Z",
    )
    dataset = PerformanceIngestionService().ingest([record])
    return CampaignMeasurementService().measure(campaign_id, dataset)


def novelty(similarity: float, *, repetitive: bool) -> NoveltyAssessment:
    return NoveltyAssessment(
        novelty_score=round(1 - similarity, 4),
        similarity_score=similarity,
        is_repetitive=repetitive,
        closest_entry=None,
    )


def test_detects_moderate_performance_decline() -> None:
    result = FatigueSignalService().assess(
        measurement("current", 75),
        measurement("baseline", 100),
    )

    assert result.campaign_id == "current"
    assert result.has_fatigue is True
    assert len(result.signals) == 1
    assert result.signals[0].kind == "performance-decline"
    assert result.signals[0].severity == "moderate"
    assert result.signals[0].score == 0.25
    assert result.signals[0].platform == "instagram"
    assert result.signals[0].metric == "views"


def test_marks_large_decline_as_high_severity() -> None:
    result = FatigueSignalService().assess(
        measurement("current", 50),
        measurement("baseline", 100),
    )

    assert result.signals[0].severity == "high"


def test_ignores_growth_and_small_declines() -> None:
    service = FatigueSignalService()

    growth = service.assess(measurement("growth", 120), measurement("baseline", 100))
    small_decline = service.assess(
        measurement("small-decline", 85),
        measurement("baseline", 100),
    )

    assert growth.signals == ()
    assert small_decline.signals == ()


def test_detects_content_and_visual_repetition() -> None:
    result = FatigueSignalService().assess(
        measurement("current", 100),
        measurement("baseline", 100),
        creative=[
            CreativeFatigueInput("caption-2", "content", novelty(0.75, repetitive=True)),
            CreativeFatigueInput("poster-2", "visual", novelty(0.92, repetitive=True)),
            CreativeFatigueInput("reel-2", "visual", novelty(0.3, repetitive=False)),
        ],
    )

    assert tuple(
        (signal.kind, signal.severity, signal.asset_id, signal.score)
        for signal in result.signals
    ) == (
        ("content-repetition", "moderate", "caption-2", 0.75),
        ("visual-repetition", "high", "poster-2", 0.92),
    )


def test_orders_signals_deterministically() -> None:
    result = FatigueSignalService().assess(
        measurement("current", 50),
        measurement("baseline", 100),
        creative=[
            CreativeFatigueInput("poster", "visual", novelty(0.8, repetitive=True)),
            CreativeFatigueInput("caption", "content", novelty(0.8, repetitive=True)),
        ],
    )

    assert tuple(signal.kind for signal in result.signals) == (
        "content-repetition",
        "performance-decline",
        "visual-repetition",
    )


@pytest.mark.parametrize(
    ("decline", "severe"),
    [(0, 40), (101, 101), (30, 20)],
)
def test_rejects_invalid_thresholds(decline: float, severe: float) -> None:
    with pytest.raises(ValueError):
        FatigueSignalService(
            decline_threshold=decline,
            severe_decline_threshold=severe,
        )


@pytest.mark.parametrize("medium", ["", "video", "graphic"])
def test_rejects_invalid_medium(medium: str) -> None:
    with pytest.raises(ValueError, match="medium"):
        FatigueSignalService().assess(
            measurement("current", 100),
            measurement("baseline", 100),
            creative=[
                CreativeFatigueInput("asset", medium, novelty(0.8, repetitive=True))
            ],
        )


def test_rejects_duplicate_asset_medium_inputs() -> None:
    item = CreativeFatigueInput("poster", "visual", novelty(0.8, repetitive=True))

    with pytest.raises(ValueError, match="duplicate"):
        FatigueSignalService().assess(
            measurement("current", 100),
            measurement("baseline", 100),
            creative=[item, item],
        )
