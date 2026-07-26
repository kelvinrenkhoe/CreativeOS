import pytest

from services.campaign_measurement import CampaignMeasurementService
from services.performance_ingestion import (
    PerformanceIngestionService,
    PerformanceRecord,
)


def record(**overrides: object) -> PerformanceRecord:
    values = {
        "asset_id": "campaign-poster",
        "platform": "instagram",
        "external_id": "post-123",
        "metric": "views",
        "value": 100,
        "observed_at": "2026-07-26T08:00:00Z",
    }
    values.update(overrides)
    return PerformanceRecord(**values)


def dataset(*records: PerformanceRecord):
    return PerformanceIngestionService().ingest(records)


def test_uses_latest_cumulative_observation_without_double_counting() -> None:
    observations = dataset(
        record(value=100, observed_at="2026-07-26T08:00:00Z"),
        record(value=175, observed_at="2026-07-27T08:00:00Z"),
    )

    measurement = CampaignMeasurementService().measure("growth-campaign", observations)

    assert measurement.campaign_id == "growth-campaign"
    assert measurement.asset_ids == ("campaign-poster",)
    assert measurement.metrics[0].value == 175
    assert measurement.metrics[0].publication_count == 1
    assert measurement.metrics[0].latest_observed_at == "2026-07-27T08:00:00Z"


def test_aggregates_publications_by_platform_and_metric() -> None:
    observations = dataset(
        record(asset_id="poster", external_id="post-1", value=125),
        record(asset_id="teaser", external_id="post-2", value=275),
        record(asset_id="teaser", external_id="post-2", metric="likes", value=40),
    )

    measurement = CampaignMeasurementService().measure("growth-campaign", observations)

    assert tuple((item.metric, item.value) for item in measurement.metrics) == (
        ("likes", 40.0),
        ("views", 400.0),
    )
    assert measurement.metrics[1].asset_count == 2
    assert measurement.metrics[1].publication_count == 2


def test_filters_measurement_to_selected_campaign_assets() -> None:
    observations = dataset(
        record(asset_id="poster", external_id="post-1", value=125),
        record(asset_id="other-campaign", external_id="post-2", value=900),
    )

    measurement = CampaignMeasurementService().measure(
        "growth-campaign",
        observations,
        asset_ids=[" poster "],
    )

    assert measurement.asset_ids == ("poster",)
    assert measurement.metrics[0].value == 125


def test_returns_empty_measurement_when_no_assets_match() -> None:
    measurement = CampaignMeasurementService().measure(
        "growth-campaign",
        dataset(record()),
        asset_ids=["missing"],
    )

    assert measurement.asset_ids == ()
    assert measurement.metrics == ()


def test_compares_campaign_measurements_deterministically() -> None:
    service = CampaignMeasurementService()
    baseline = service.measure(
        "baseline",
        dataset(
            record(metric="likes", value=20),
            record(metric="views", value=100),
        ),
    )
    current = service.measure(
        "current",
        dataset(
            record(metric="shares", value=15),
            record(metric="views", value=150),
        ),
    )

    comparison = service.compare(current, baseline)

    assert comparison.baseline_campaign_id == "baseline"
    assert comparison.current_campaign_id == "current"
    assert tuple(
        (
            item.metric,
            item.baseline_value,
            item.current_value,
            item.absolute_change,
            item.percentage_change,
        )
        for item in comparison.metrics
    ) == (
        ("likes", 20.0, 0.0, -20.0, -100.0),
        ("shares", 0.0, 15.0, 15.0, None),
        ("views", 100.0, 150.0, 50.0, 50.0),
    )


@pytest.mark.parametrize("campaign_id", ["", "   "])
def test_rejects_empty_campaign_id(campaign_id: str) -> None:
    with pytest.raises(ValueError, match="campaign_id"):
        CampaignMeasurementService().measure(campaign_id, dataset())


def test_rejects_empty_selected_asset_id() -> None:
    with pytest.raises(ValueError, match="asset_id"):
        CampaignMeasurementService().measure("campaign", dataset(), asset_ids=[" "])
