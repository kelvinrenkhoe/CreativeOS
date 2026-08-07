# CreativeOS Command Reference

## Organizations

CreativeOS organizes customer and business data beneath the `organizations/` repository boundary.
Commands discover the nearest parent repository that contains this directory, so they can be run
from nested paths within the repository.

### `creativeos org list`

List all valid organizations discovered in the current CreativeOS repository.

### `creativeos org show <organization-id>`

Display the identity, type, and description of one organization.

Example:

```bash
creativeos org show kre
```

### `creativeos org validate`

Validate every discovered organization and its safe repository path.

```bash
creativeos org validate
```

Organization identifiers are restricted to lowercase letters, numbers, and internal hyphens.
Path-like identifiers are rejected to keep organization data inside the `organizations/` boundary.

## Execution Engine

Execution commands operate on one organization project campaign and discover the repository from the
current directory. Organization, project, and campaign identifiers are explicit so work cannot cross
workspace boundaries accidentally.

### `creativeos execution today`

Show overdue work, actions due today, blocked work, and campaign progress.

```bash
creativeos execution today --org kre --project no-lose-guard --campaign launch
```

### `creativeos execution next`

Show the highest-value ready actions selected by the Execution Planner. Use `--limit` to control how
many actions are shown.

```bash
creativeos execution next --org kre --project no-lose-guard --campaign launch --limit 3
```

### `creativeos execution overdue`

Show unfinished actions whose due date has passed.

```bash
creativeos execution overdue --org kre --project no-lose-guard --campaign launch
```

### `creativeos execution ready`

Show actions that can be worked now because their dependencies are satisfied.

```bash
creativeos execution ready --org kre --project no-lose-guard --campaign launch
```

The existing top-level `creativeos next` content-direction command is intentionally preserved. The
Execution Engine uses the `creativeos execution` namespace to avoid breaking existing workflows.
