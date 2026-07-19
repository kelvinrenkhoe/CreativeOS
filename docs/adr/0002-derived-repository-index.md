# ADR 0002: Treat the repository index as derived state

- Status: Accepted
- Date: 2026-07-18

## Context

CreativeOS needs fast discovery and search across songs, campaigns, books, and assets. Rewalking the repository for every operation will become increasingly expensive as workspaces grow.

The Git repository is already the authoritative source of creative data under ADR 0001. Introducing another authoritative store would create synchronization and ownership problems.

## Decision

CreativeOS will maintain a disposable repository index under `.creativeos/index.json`.

The index:

- is generated from repository content;
- may be deleted and rebuilt at any time;
- must never become the authoritative source of creative data;
- stores repository-relative paths so it remains portable;
- uses a version field to support future schema changes.

## Consequences

Repository reads can use the index for speed while preserving the filesystem and Git history as the source of truth. CreativeOS must detect missing, corrupt, incompatible, or stale indexes and provide a safe rebuild path.
