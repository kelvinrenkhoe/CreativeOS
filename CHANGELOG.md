# Changelog

All notable changes to CreativeOS will be documented in this file.

The format follows Keep a Changelog, and this project uses Semantic Versioning.

## [Unreleased]

### Added

- GitHub Actions workflow for linting, formatting checks, and tests.
- Development dependency group for pytest, pytest-cov, and Ruff.
- Ruff linting and formatting configuration.
- Contributor guide and development commands.
- MIT license text.
- Organization CLI commands for listing, showing, and validating repository organizations.
- Organization repository discovery from nested directories.
- Organization-scoped project contexts under `organizations/<organization>/projects/<project>`.
- Safe project discovery, loading, validation, and path isolation.
- Initial KRE `no-lose-guard` project context.
- Project-scoped campaign contexts under `organizations/<organization>/projects/<project>/campaigns/<campaign>`.
- Safe campaign discovery, loading, date validation, and path isolation.
- Initial KRE `no-lose-guard` launch campaign context.
- Immutable campaign `Action` model for executable marketing work, including lifecycle status, priority, due dates, channels, and dependencies.
- Campaign-scoped `ActionRepository` for safe YAML persistence, listing, loading, deletion, and campaign isolation.
- `ActionService` business behaviour for lifecycle transitions, dependency readiness, due-date queries, validation, and campaign progress.
- `ExecutionPlanner` for deterministic campaign execution plans and prioritized next-action selection.
- Execution Engine CLI commands for today, next, overdue, and ready campaign work views.
- Top-level `creativeos today` Daily Brief combining campaign context, execution priorities, blockers, overdue work, and progress.
- Execution CLI lifecycle commands for completing, blocking, unblocking, cancelling, and reopening campaign actions.
- Execution CLI `add` command for creating validated campaign actions with priority, due date, channel, description, and dependencies.
- Reusable execution templates with dependency-safe preview and bulk apply commands.
- Generic `awareness-campaign` execution template as the first built-in plan.
- Parameterised execution template variables with required/default values and `--var key=value` CLI overrides.
- Generic `scheduled-awareness-campaign` template demonstrating reusable campaign date, channel, and audience inputs.
- Relative template scheduling expressions such as `{{ launch_date - 14d }}` and `{{ launch_date + 3d }}`.
- Generic `launch-timeline` execution template for pre-launch, launch-day, and post-launch scheduling from one anchor date.
- Named campaign milestones stored in campaign metadata and available as reusable execution-template date anchors.
- Generic `milestone-campaign` template coordinating content freeze, launch, and performance review milestones.
- Campaign milestone CLI commands for listing, setting, and removing validated milestone dates without hand-editing campaign YAML.
- Milestone-aware Daily Brief showing campaign milestones as upcoming, due today, or overdue relative to the brief date.
- Milestone focus and urgency labels in the Daily Brief, highlighting the nearest current or future milestone while preserving action-priority rules.
- Milestone-linked campaign actions and Daily Brief focus-milestone work views.
- Execution templates that automatically assign generated actions to their relevant campaign milestones.
- Milestone-aware execution plan preview output showing each generated action's target milestone before apply.
- Milestone progress summaries showing completed, ready, pending, blocked, total, and completion percentage for linked campaign work.
- Deterministic milestone health indicators combining deadline proximity and linked-work progress without changing execution order.
- Milestone attention summaries explaining at-risk and watch conditions, exception counts, and progress without changing action priority.
- Deterministic milestone intervention suggestions for attention-worthy work, kept advisory and separate from execution priority.
- Campaign-level decision summaries that consolidate milestone health, attention, and intervention signals without changing execution order.
- Preview-first `campaign start` workflow for milestone-ready music-release campaigns scoped to an organization project.

### Changed

- Updated the package description to reflect CreativeOS as a repository-native automation platform.

## [0.2.0-alpha] - 2026-07-18

### Added

- Introduced the `Song` model.
- Added `SongService` for song workspace creation.
- Added `ScaffoldService` for reusable workspace scaffolding.
- Added modular CLI command groups.
- Implemented `creativeos song new`.
- Added song scaffold definition.
- Added workspace discovery from nested directories.
- Added `creativeos doctor` environment and project diagnostics.
- Added CLI version command.
- Added automated tests for discovery and diagnostics.

### Changed

- Refactored the CLI into modular command groups.
- Established the service layer for business capabilities.

## [0.1.0] - 2026-07-01

### Added

- Initial CreativeOS package structure.
- Typer-based CLI foundation.
- Project status command.
