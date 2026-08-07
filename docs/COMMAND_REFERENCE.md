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
