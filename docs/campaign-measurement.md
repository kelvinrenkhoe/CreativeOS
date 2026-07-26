# Campaign Measurement

CreativeOS turns normalized performance observations into deterministic campaign-level
measurements with `CampaignMeasurementService`.

## Measurement contract

`measure(campaign_id, dataset, asset_ids=...)` can scope a performance dataset to the
assets belonging to one campaign. For each asset, platform, external publication, and
metric series, the service selects the latest observation before aggregating values by
platform and metric.

Selecting the latest value prevents cumulative platform snapshots from being added
together repeatedly. A metric summary includes:

- the normalized platform and metric names
- the aggregate value
- the number of contributing assets and publications
- the latest observation timestamp

Results and asset identifiers are returned in deterministic order. A campaign with no
matching observations produces an empty measurement rather than fabricated zero-valued
metrics.

## Comparisons

`compare(current, baseline)` compares the union of platform metrics in two campaign
measurements. Every comparison includes baseline and current values, absolute change,
and percentage change. Percentage change is `None` when the baseline is zero because
a meaningful percentage cannot be calculated.

The comparison is mathematical only. CreativeOS does not label an increase or decrease
as good or bad because the meaning depends on the metric and campaign objective.

## Integration boundary

This capability consumes `PerformanceDataset` from the performance-ingestion layer.
It performs no provider API calls, credential handling, persistence, fatigue detection,
or recommendation learning. Those responsibilities remain with adapters and later
analytics capabilities.
