# Operations Dashboard and Audit History

The operations layer provides a read-only view of campaign execution and a small,
provider-neutral audit record.

## Audit history

`AuditHistoryService.record()` appends a validated `AuditEvent` to immutable
`AuditHistory`. Each event identifies:

- when the action happened;
- its operational category and action;
- the affected campaign, request, asset, or other subject;
- the human or service actor;
- optional evidence and detail references.

Event IDs are unique, timestamps must include a timezone, and supported categories are
campaign, approval, queue, execution, publishing, and measurement. Recording history
does not mutate a campaign run or queue.

## Dashboard snapshot

`OperationsDashboardService.build()` projects existing `CampaignRun`,
`ExecutionQueue`, and `AuditHistory` values into:

- campaign stages and required next actions;
- queue totals grouped by status;
- failed execution jobs and their reasons;
- a configurable list of recent audit events.

The output is deterministic and contains no worker, provider, publishing, scheduler,
persistence, or lifecycle-transition behaviour. A CLI, API, or later visual interface
can render this read model without gaining permission to change the underlying state.

## Example

```python
dashboard = OperationsDashboardService().build(
    campaign_runs,
    execution_queue,
    audit_history,
    recent_event_limit=20,
)
```

Operational actions should still be performed by their owning services. After an
action succeeds, its caller can append the corresponding audit event and rebuild the
dashboard from the resulting immutable state.
