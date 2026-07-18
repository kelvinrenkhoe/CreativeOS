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
