"""Read Instagram media insights into provider-neutral performance records."""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from services.performance_ingestion import (
    PerformanceDataset,
    PerformanceIngestionService,
    PerformanceRecord,
)
from services.provider_configuration import ProviderConfigurationError, SecretSource


class InstagramAnalyticsError(RuntimeError):
    """Report a secret-safe Instagram analytics failure."""


@dataclass(frozen=True, slots=True)
class InstagramAnalyticsConfiguration:
    """Non-secret configuration for Instagram media insights."""

    credential_ref: str
    endpoint: str
    metrics: tuple[str, ...]
    timeout_seconds: int = 60


@dataclass(frozen=True, slots=True)
class InstagramPublication:
    """Map one CreativeOS asset to its published Instagram media ID."""

    asset_id: str
    media_id: str


class InstagramAnalyticsTransport:
    """Small read-only Graph API boundary."""

    def __init__(self, credential: str, *, endpoint: str, timeout: int) -> None:
        self._credential = credential
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout

    def request(self, path: str, parameters: dict[str, str]) -> dict[str, Any]:
        values = dict(parameters)
        values["access_token"] = self._credential
        url = f"{self._endpoint}{path}?{urllib.parse.urlencode(values)}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read())
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise InstagramAnalyticsError("Instagram analytics request failed") from error


class InstagramAnalyticsConnector:
    """Fetch configured metrics without mutating publication or campaign state."""

    def __init__(
        self,
        transport: Any,
        *,
        metrics: tuple[str, ...],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._transport = transport
        self._metrics = self._normalize_metrics(metrics)
        self._clock = clock

    @property
    def platform(self) -> str:
        return "instagram"

    def ingest(self, publications: Iterable[InstagramPublication]) -> PerformanceDataset:
        records: list[PerformanceRecord] = []
        identities: set[tuple[str, str]] = set()

        for publication in publications:
            asset_id = self._required(publication.asset_id, "asset_id")
            media_id = self._required(publication.media_id, "media_id")
            identity = (asset_id, media_id)
            if identity in identities:
                raise ValueError("duplicate Instagram publication")
            identities.add(identity)
            response = self._transport.request(
                f"/{media_id}/insights",
                {"metric": ",".join(self._metrics)},
            )
            records.extend(self._records(asset_id, media_id, response))

        return PerformanceIngestionService().ingest(records)

    def _records(
        self,
        asset_id: str,
        media_id: str,
        response: dict[str, Any],
    ) -> tuple[PerformanceRecord, ...]:
        observed_at = self._timestamp(self._clock())
        records: list[PerformanceRecord] = []
        data = response.get("data")
        if not isinstance(data, list):
            raise InstagramAnalyticsError("Instagram returned invalid analytics data")

        for item in data:
            if not isinstance(item, dict):
                raise InstagramAnalyticsError("Instagram returned invalid analytics data")
            metric = str(item.get("name", "")).strip()
            value, timestamp = self._observation(item, observed_at)
            records.append(
                PerformanceRecord(
                    asset_id=asset_id,
                    platform=self.platform,
                    external_id=media_id,
                    metric=metric,
                    value=value,
                    observed_at=timestamp,
                )
            )
        return tuple(records)

    @staticmethod
    def _observation(item: dict[str, Any], fallback: str) -> tuple[float, str]:
        total = item.get("total_value")
        if isinstance(total, dict) and "value" in total:
            return total["value"], fallback

        values = item.get("values")
        if isinstance(values, list) and values:
            latest = values[-1]
            if isinstance(latest, dict) and "value" in latest:
                return latest["value"], str(latest.get("end_time", fallback))
        raise InstagramAnalyticsError("Instagram metric has no numeric observation")

    @classmethod
    def _normalize_metrics(cls, metrics: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(cls._required(metric, "metric").casefold() for metric in metrics)
        if not normalized:
            raise ProviderConfigurationError("Instagram analytics requires at least one metric")
        if len(normalized) != len(set(normalized)):
            raise ProviderConfigurationError("Instagram analytics metrics must be unique")
        return normalized

    @staticmethod
    def _timestamp(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise InstagramAnalyticsError("analytics clock must be timezone-aware")
        return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ProviderConfigurationError(f"Instagram analytics {field} must not be empty")
        return normalized


class InstagramAnalyticsConnectorFactory:
    """Resolve a credential only while constructing the analytics transport."""

    def __init__(self, transport_factory: Callable[..., Any] = InstagramAnalyticsTransport) -> None:
        self._transport_factory = transport_factory

    def create(
        self,
        configuration: InstagramAnalyticsConfiguration,
        secret_source: SecretSource,
    ) -> InstagramAnalyticsConnector:
        credential_ref = InstagramAnalyticsConnector._required(
            configuration.credential_ref,
            "credential_ref",
        )
        endpoint = InstagramAnalyticsConnector._required(configuration.endpoint, "endpoint")
        metrics = InstagramAnalyticsConnector._normalize_metrics(configuration.metrics)
        if configuration.timeout_seconds < 1:
            raise ProviderConfigurationError("Instagram timeout_seconds must be at least 1")

        credential = secret_source.resolve(credential_ref)
        transport = self._transport_factory(
            credential,
            endpoint=endpoint,
            timeout=configuration.timeout_seconds,
        )
        return InstagramAnalyticsConnector(transport, metrics=metrics)
