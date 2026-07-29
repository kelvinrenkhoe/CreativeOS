# Instagram Analytics Ingestion Connector

CreativeOS can import media-level Instagram Insights into the existing provider-neutral
performance dataset. The connector is read-only: it never publishes content, edits a post,
or changes campaign state.

## Configuration

- credential reference: normally `INSTAGRAM_ACCESS_TOKEN`
- endpoint: an explicitly selected Meta Graph API version
- metrics: the exact media insight metrics required by the campaign
- request timeout

The access token is resolved only while constructing the HTTP transport. It is not copied into
publications, performance records, datasets, logs, or errors.

## Ingestion lifecycle

The caller supplies explicit mappings between stable CreativeOS asset IDs and Instagram media
IDs. For each mapping, the connector requests the configured insight metrics and supports both
aggregate `total_value` responses and time-series `values` responses. Aggregate observations use
the connector's timezone-aware collection time; time-series observations retain the provider's
latest timestamp.

Every observation is passed through `PerformanceIngestionService`, which normalizes metric names
and timestamps, rejects duplicate identities, and returns deterministic immutable records.
Campaign measurement, fatigue detection, and recommendation learning continue to consume that
provider-neutral dataset without depending on Instagram.

## Operational boundary

This milestone does not discover accounts, infer asset mappings, store credentials, schedule
collection, persist datasets, judge performance, or mutate campaigns. Other platforms can add
connectors behind the same existing ingestion boundary without changing the analytics domain.
