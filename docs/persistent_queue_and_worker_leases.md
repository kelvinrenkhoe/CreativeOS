# Persistent Queue and Worker Leases

CreativeOS can persist an approved execution queue and coordinate multiple worker
processes without allowing the same request to be executed concurrently.

## Boundary

`JsonExecutionQueueStore` owns two pieces of durable state:

- the complete immutable `ExecutionQueue`;
- active `WorkerLease` records for scheduled requests.

The snapshot is versioned JSON. Writes use a temporary file plus `os.replace`, and
reads, writes, leases, renewals, releases, and commits are serialized with a file
lock. The implementation is local-first and introduces no database, daemon, cloud
queue, credentials, or provider SDK.

## Processing one job

1. Save or load a `PersistentQueue`.
2. Call `lease_next(...)` with a worker identity, current timezone-aware time, and
   positive lease duration.
3. If no due unleased request exists, the method returns `None`.
4. Pass the returned queue snapshot to `QueueWorkerService.run_next(...)`.
5. Commit the worker's completed or failed queue with the exact returned lease.

A stored job remains scheduled while its lease is active. The lease is the durable
claim. This lets an expired lease make abandoned work eligible again instead of
leaving the queue permanently stuck in a claimed state.

## Fencing and recovery

Only one active lease may reference a request. The store rejects a commit when the
lease ID, request ID, or worker ID does not match current durable state, or when the
lease has expired. A successful commit must change only the leased request and must
leave it completed or failed.

Workers that need more time can renew an active lease. A worker that stops before
provider execution can release it without changing the queued job. Expired leases
are removed during the next lease, renew, release, or commit transaction.

## Current limitations

This milestone deliberately uses a local filesystem lock and JSON snapshot. It does
not coordinate across different machines or shared object storage. A future
production store can implement the same atomic lease and fencing semantics using a
transactional database or managed queue without changing provider adapters.
