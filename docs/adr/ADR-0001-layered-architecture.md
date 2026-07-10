# ADR-0001: Layered Architecture

## Status

Accepted

## Context

CreativeOS is expected to grow into a platform supporting multiple creator workflows.
A clear separation of responsibilities is required to maintain long-term simplicity.

## Decision

CreativeOS adopts a layered architecture:

Presentation (CLI)

↓

Application Services

↓

Domain Models

↓

Infrastructure

Business logic must reside in services.

Models represent domain concepts.

The CLI is responsible only for user interaction.

Infrastructure handles filesystem and configuration concerns.

## Consequences

Positive

- Easier testing
- Better reuse
- Clear ownership
- Predictable architecture

Negative

- Slightly more files
- More upfront design
