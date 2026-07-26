import pytest

from services.performance_ingestion import (
    PerformanceIngestionService,
    PerformanceRecord,
)


def record(**overrides: object) -> PerformanceRecord:
    values = {
        "asset_id": " no-way-back-poster ",
        "platform": " Instagram ",
        "external_id": " post-123 ",
        "metric": " Video Views ",
        "value": 1250,
        "observed_at": "2026-07-26T08:30:00+01:00",
    }
    values.update(overrides)
    return PerformanceRecord(**values)


def test_normalizes_provider_neutral_performance_record() -> None:
    dataset = PerformanceIngestionService().ingest([record()])

    assert dataset.records == (
        PerformanceRecord(
            asset_id="no-way-back-poster",
            platform="instagram",
            external_id="post-123",
            metric="video-views",
            value=1250.0,
            observed_at="2026-07-26T07:30:00Z",
        ),
    )


def test_orders_records_deterministically() -> None:
    later = record(metric="likes", observed_at="2026-07-27T08:00:00Z")
    earlier = record(metric="shares", observed_at="2026-07-26T08:00:00Z")

    dataset = PerformanceIngestionService().ingest([later, earlier])

    assert tuple(item.metric for item in dataset.records) == ("shares", "likes")


@pytest.mark.parametrize("field", ["asset_id", "platform", "external_id", "metric"])
def test_rejects_empty_identifiers(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        PerformanceIngestionService().ingest([record(**{field: " "})])


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_rejects_invalid_metric_values(value: float) -> None:
    with pytest.raises(ValueError, match="non-negative finite"):
        PerformanceIngestionService().ingest([record(value=value)])


def test_requires_timezone_aware_iso_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone"):
        PerformanceIngestionService().ingest(
            [record(observed_at="2026-07-26T08:30:00")]
        )


def test_rejects_duplicate_observations_after_normalization() -> None:
    duplicate = record(platform="instagram", metric="video_views")

    with pytest.raises(ValueError, match="duplicate"):
        PerformanceIngestionService().ingest([record(), duplicate])
