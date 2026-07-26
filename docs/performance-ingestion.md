# Performance Ingestion

CreativeOS uses a provider-neutral ingestion boundary for performance data.

`PerformanceIngestionService` accepts observations that have already been fetched
or imported by an external integration. Each observation links a platform metric to
both the CreativeOS asset ID and the platform's external publication ID.

## Record contract

A `PerformanceRecord` contains:

- `asset_id`: the stable CreativeOS asset identifier.
- `platform`: the source platform.
- `external_id`: the provider's publication identifier.
- `metric`: a provider-neutral or provider-supplied metric name.
- `value`: a non-negative finite numeric observation.
- `observed_at`: a timezone-aware ISO 8601 timestamp.

The service trims identifiers, normalizes platform and metric names, converts
timestamps to UTC, rejects duplicate observations, and returns records in a
deterministic order.

## Integration boundary

Platform adapters are responsible for credentials, API requests, pagination, rate
limits, and mapping provider responses into `PerformanceRecord` objects. The core
service performs no network calls and stores no credentials.

This milestone does not aggregate metrics or judge campaign performance. Campaign
measurement, fatigue signals, and recommendation learning consume the normalized
dataset in later capabilities.
