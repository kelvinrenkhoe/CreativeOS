# Campaign Scheduling and Queueing

Campaign scheduling places already approved provider-execution requests into a deterministic queue.
It does not approve assets, call providers, retry failures, publish outputs, or advance a campaign
run.

## Scheduling flow

`CampaignQueueService.schedule()` accepts an `ExecutionRequest`, its matching
`ExecutionApproval`, a timezone-aware execution time, and a non-negative priority. The service
normalizes the provider-facing identity and rejects duplicate request IDs across every queue status.

```python
queue = CampaignQueueService().schedule(
    queue,
    request,
    approval,
    scheduled_for=release_time,
    priority=10,
)
```

The immutable `ExecutionQueue` returned by every operation can later be stored through a
persistence adapter. This milestone intentionally provides no database, broker, timer, or
background worker.

## Queue order and lifecycle

`ready()` returns only due, unclaimed work. Jobs are ordered by:

1. highest priority;
2. earliest scheduled time;
3. request ID for a stable tie-break.

A worker may then claim one due job. Claiming records the worker identity but does not invoke a
provider adapter. The worker separately passes the claimed request and approval to
`ProviderExecutionService`, then records either:

- `complete()` with a receipt matching the exact queued request; or
- `fail()` with a human-readable reason.

Scheduled work may be cancelled only before it is claimed. Failed jobs are not silently retried,
which prevents duplicate provider execution. A future retry policy can schedule a deliberate new
request identity after human review.

## Safety boundary

The queue preserves the approval attached to the original asset, media type, and provider. It does
not change prompts, choose providers, generate media, manage credentials, poll provider jobs,
publish content, or create orchestration evidence. Those responsibilities remain with their
existing CreativeOS boundaries.
