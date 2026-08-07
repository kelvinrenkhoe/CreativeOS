# Organizations

`organizations/` contains customer and business-specific CreativeOS workspace data.

CreativeOS platform code remains organization-agnostic. An organization owns its own brand context, knowledge, projects, campaigns, assets, channels, analytics, and memory.

The stable hierarchy is:

```text
Organization
└── Project
    └── Campaign
        ├── Actions
        ├── Creative Assets
        ├── Publishing
        ├── Analytics
        └── Learning
```

Each organization directory must contain an `organization.yaml` file whose `id` matches the directory name.

Example:

```text
organizations/
└── kre/
    ├── organization.yaml
    └── projects/
        └── no-lose-guard/
            ├── project.yaml
            └── campaigns/
                └── launch/
```

Organization IDs are lowercase, path-safe identifiers using letters, numbers, and internal hyphens. Core platform logic must never hardcode a particular organization, creator, industry, project type, or marketing channel.

`kre` is the first production organization used to validate CreativeOS with real campaigns. Future organizations should use the same contract rather than introducing customer-specific platform code.
