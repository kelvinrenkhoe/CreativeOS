"""Aggregate normalized observations into deterministic campaign measurements."""

from collections.abc import Iterable
from dataclasses import dataclass

from services.performance_ingestion import PerformanceDataset, PerformanceRecord


@dataclass(frozen=True, slots=True)
class CampaignMetricSummary:
    """The latest aggregate value for one platform metric."""

    platform: str
    metric: str
    value: float
    asset_count: int
    publication_count: int
    latest_observed_at: str


@dataclass(frozen=True, slots=True)
class CampaignMeasurement:
    """Campaign-level performance derived from normalized observations."""

    campaign_id: str
    asset_ids: tuple[str, ...]
    metrics: tuple[CampaignMetricSummary, ...]


@dataclass(frozen=True, slots=True)
class CampaignMetricComparison:
    """A current metric compared with a baseline metric."""

    platform: str
    metric: str
    baseline_value: float
    current_value: float
    absolute_change: float
    percentage_change: float | None


@dataclass(frozen=True, slots=True)
class CampaignComparison:
    """Deterministic metric differences between two campaign measurements."""

    baseline_campaign_id: str
    current_campaign_id: str
    metrics: tuple[CampaignMetricComparison, ...]


class CampaignMeasurementService:
    """Measure campaigns without interpreting whether results are good or bad."""

    def measure(
        self,
        campaign_id: str,
        dataset: PerformanceDataset,
        *,
        asset_ids: Iterable[str] | None = None,
    ) -> CampaignMeasurement:
        """Aggregate the latest value from every matching publication metric series."""
        normalized_campaign_id = self._required(campaign_id, "campaign_id")
        selected_assets = self._asset_ids(asset_ids)
        records = (
            dataset.records
            if selected_assets is None
            else tuple(record for record in dataset.records if record.asset_id in selected_assets)
        )
        latest = self._latest_records(records)
        grouped: dict[tuple[str, str], list[PerformanceRecord]] = {}

        for record in latest:
            grouped.setdefault((record.platform, record.metric), []).append(record)

        metrics = tuple(
            self._summarize(platform, metric, items)
            for (platform, metric), items in sorted(grouped.items())
        )
        measured_assets = tuple(sorted({record.asset_id for record in latest}))
        return CampaignMeasurement(
            campaign_id=normalized_campaign_id,
            asset_ids=measured_assets,
            metrics=metrics,
        )

    def compare(
        self,
        current: CampaignMeasurement,
        baseline: CampaignMeasurement,
    ) -> CampaignComparison:
        """Compare the union of metrics in current and baseline measurements."""
        current_metrics = {
            (summary.platform, summary.metric): summary.value for summary in current.metrics
        }
        baseline_metrics = {
            (summary.platform, summary.metric): summary.value for summary in baseline.metrics
        }
        keys = sorted(current_metrics.keys() | baseline_metrics.keys())
        comparisons = tuple(
            self._comparison(
                platform,
                metric,
                current_metrics.get((platform, metric), 0.0),
                baseline_metrics.get((platform, metric), 0.0),
            )
            for platform, metric in keys
        )
        return CampaignComparison(
            baseline_campaign_id=baseline.campaign_id,
            current_campaign_id=current.campaign_id,
            metrics=comparisons,
        )

    @staticmethod
    def _latest_records(records: Iterable[PerformanceRecord]) -> tuple[PerformanceRecord, ...]:
        latest: dict[tuple[str, str, str, str], PerformanceRecord] = {}
        for record in records:
            key = (record.asset_id, record.platform, record.external_id, record.metric)
            existing = latest.get(key)
            if existing is None or record.observed_at > existing.observed_at:
                latest[key] = record
        return tuple(latest[key] for key in sorted(latest))

    @staticmethod
    def _summarize(
        platform: str,
        metric: str,
        records: list[PerformanceRecord],
    ) -> CampaignMetricSummary:
        return CampaignMetricSummary(
            platform=platform,
            metric=metric,
            value=sum(record.value for record in records),
            asset_count=len({record.asset_id for record in records}),
            publication_count=len({(record.asset_id, record.external_id) for record in records}),
            latest_observed_at=max(record.observed_at for record in records),
        )

    @staticmethod
    def _comparison(
        platform: str,
        metric: str,
        current_value: float,
        baseline_value: float,
    ) -> CampaignMetricComparison:
        absolute_change = current_value - baseline_value
        percentage_change = (
            None if baseline_value == 0 else (absolute_change / baseline_value) * 100
        )
        return CampaignMetricComparison(
            platform=platform,
            metric=metric,
            baseline_value=baseline_value,
            current_value=current_value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
        )

    @classmethod
    def _asset_ids(cls, values: Iterable[str] | None) -> frozenset[str] | None:
        if values is None:
            return None
        return frozenset(cls._required(value, "asset_id") for value in values)

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
