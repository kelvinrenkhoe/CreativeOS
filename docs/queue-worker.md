# Controlled Queue Worker

The queue worker is the first Phase 6 production-integration boundary. It connects approved,
scheduled work to the existing provider execution service without adding a daemon or embedding
provider credentials in CreativeOS.

`QueueWorkerService.run_next(...)`:

1. selects the first due job using `CampaignQueueService.ready`;
2. claims exactly that job for a named worker;
3. resolves one adapter matching its provider and media type;
4. executes through `ProviderExecutionService`, preserving the original approval checks;
5. completes the queue job with its matching receipt or records a visible failure; and
6. appends attributable execution events to `AuditHistory`.

Retries are bounded by `max_attempts`. Only adapters that raise
`RetryableProviderError` request another attempt. Validation errors, missing or ambiguous
adapters, and other permanent failures stop immediately. Every retry is retained in the returned
attempt evidence and audit history.

This service runs one job per call. Scheduling loops, concurrency, leases, persistence,
credentials, backoff timing, and real Veo, Runway, Kling, or image-provider adapters remain
deployment concerns for later milestones.
