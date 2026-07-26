"""Normalize provider-neutral performance observations for later analysis."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class PerformanceRecord:
    """One externally observed metric tied to a published CreativeOS asset."""

    asset_id: str
    platform: str
    external_id: str
    metric: str
    value: float
    observed_at: str


@dataclass(frozen=True, slots=True)
class PerformanceDataset:
    """Validated, deterministic performance observations."""

    records: tuple[PerformanceRecord, ...]


class PerformanceIngestionService:
    """Normalize external observations without depending on provider APIs."""

    def ingest(self, records: Iterable[PerformanceRecord]) -> PerformanceDataset:
        """Validate, normalize, de-duplicate, and order performance records."""
        normalized: list[PerformanceRecord] = []
        identities: set[tuple[str, str, str, str, str]] = set()

        for record in records:
            item = self._normalize(record)
            identity = (
                item.asset_id,
                item.platform,
                item.external_id,
                item.metric,
                item.observed_at,
            )
            if identity in identities:
                raise ValueError("duplicate performance observation")
            identities.add(identity)
            normalized.append(item)

        normalized.sort(
            key=lambda item: (
                item.observed_at,
                item.platform,
                item.asset_id,
                item.external_id,
                item.metric,
            )
        )
        return PerformanceDataset(records=tuple(normalized))

    @classmethod
    def _normalize(cls, record: PerformanceRecord) -> PerformanceRecord:
        value = cls._value(record.value)
        observed_at = cls._timestamp(record.observed_at)

        return PerformanceRecord(
            asset_id=cls._required(record.asset_id, "asset_id"),
            platform=cls._slug(record.platform, "platform"),
            external_id=cls._required(record.external_id, "external_id"),
            metric=cls._slug(record.metric, "metric"),
            value=value,
            observed_at=observed_at,
        )

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized

    @classmethod
    def _slug(cls, value: str, field: str) -> str:
        return "-".join(cls._required(value, field).casefold().replace("_", " ").split())

    @staticmethod
    def _value(value: float) -> float:
        if isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("value must be a non-negative finite number")
        return float(value)

    @classmethod
    def _timestamp(cls, value: str) -> str:
        raw = cls._required(value, "observed_at")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("observed_at must be a valid ISO 8601 timestamp") from error
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
