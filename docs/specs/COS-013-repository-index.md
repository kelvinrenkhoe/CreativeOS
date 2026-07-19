# COS-013: Repository Index

## Purpose

Provide a fast, deterministic, and disposable view of repository content without changing CreativeOS's repository-first architecture.

## Scope

COS-013 introduces:

- typed index domain models;
- index construction from the Repository API;
- JSON persistence at `.creativeos/index.json`;
- load, refresh, validate, and statistics operations;
- CLI commands for building and inspecting the index.

## Domain model

`IndexEntry` records an entity type, slug, display name, and repository-relative path.

`RepositoryStats` records counts for songs, campaigns, books, and assets.

`RepositoryIndex` records the schema version, generation time, statistics, and immutable entries.

## Invariants

- Git and repository files remain authoritative.
- Index paths are relative to the workspace root.
- Index generation is deterministic for unchanged repository content.
- A missing or corrupt index must not cause data loss.
- Duplicate repository slugs remain errors.

## Planned CLI

```bash
creativeos index build
creativeos index refresh
creativeos index stats
creativeos index validate
```

## Definition of done

- Index models, service, persistence, and CLI are implemented.
- Missing and corrupt index files are handled clearly.
- Unit tests cover build, save, load, refresh, validation, and statistics.
- Ruff and Pytest pass in CI.
