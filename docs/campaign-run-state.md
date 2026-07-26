# Persistent Campaign Run State

Campaign run persistence preserves an orchestration run between processes without changing its
lifecycle. The saved snapshot includes the campaign plan, cinematic treatment, video prompt,
image plan, current stage, and every approval or execution evidence record.

## Storage boundary

`CampaignRunStore` is the provider-neutral persistence protocol. `JsonCampaignRunStore` is the
first adapter and writes one versioned JSON file per campaign ID. Saving atomically replaces the
previous snapshot, so a run can be checkpointed after each successful lifecycle transition.

```python
store = JsonCampaignRunStore(project_root / ".creativeos" / "campaign-runs")
store.save(run)
resumed = store.load(run.campaign_id)
```

A later database or remote-object adapter can implement the same protocol without changing
campaign orchestration.

## Restore validation

Loading reconstructs the complete typed `CampaignRun` and validates:

- the snapshot schema version;
- the requested and stored campaign IDs;
- matching work IDs across every embedded plan;
- a supported lifecycle stage;
- the exact evidence sequence required by that stage;
- non-empty evidence references and human recorder identities.

Invalid, corrupt, missing, or unsupported snapshots raise specific persistence errors. Loading
never advances a stage, records evidence, calls a provider, publishes content, or fetches
analytics.

## Operational boundary

The application should save only after an orchestration transition succeeds. Provider execution,
scheduling, queueing, dashboards, and audit history remain separate Phase 5 capabilities.
