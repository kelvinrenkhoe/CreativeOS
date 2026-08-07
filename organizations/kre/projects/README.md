# KRE Projects

Projects are durable pieces of work owned by Kelvin Rankie Entertainment, such as a song, book, event, album, or other creative initiative.

Each project may own one or more campaigns.

```text
projects/
└── <project-id>/
    ├── project.yaml
    ├── knowledge/
    ├── assets/
    ├── campaigns/
    │   └── <campaign-id>/
    │       ├── campaign.yaml
    │       ├── actions/
    │       ├── creative/
    │       ├── publishing/
    │       ├── analytics/
    │       └── memory/
    └── analytics/
```

For example, `no-lose-guard` is a project. Its pre-release, launch-week, radio, playlist, and post-release marketing work may be represented as separate campaigns under that project while sharing the same project knowledge and assets.
