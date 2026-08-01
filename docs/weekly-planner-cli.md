# Weekly Campaign Planner CLI

CreativeOS exposes the durable weekly content planner through:

```bash
creativeos campaign week plan <campaign-id> --week-start YYYY-MM-DD
```

`--week-start` must be a Monday. The command creates a deterministic seven-day plan when the week does not already exist and loads the stored plan on repeated invocations.

Use `--replace` only when an existing week must be rebuilt explicitly:

```bash
creativeos campaign week plan no-lose-guard \
  --week-start 2026-08-03 \
  --replace
```

Plans are stored per campaign under:

```text
.creativeos/content-plans/<campaign-id>.json
```

The command displays the scheduled date, platform, format, concept, angle, call to action, and status for each item. Every item begins in `planned` state.

## Safety

The command does not contact AI providers, publish content, advance campaign runtime checkpoints, or mark external work complete. Existing weeks are preserved unless replacement is explicit, and invalid persisted state fails closed.
