# CreativeOS Engineering Handbook

## Purpose

This document defines the engineering standards and development workflow for CreativeOS.

---

# Engineering Principles

## Creator First

CreativeOS exists to help creators spend more time creating and less time managing.

## Platform First

Build reusable capabilities before building features.

## Single Responsibility

Every module should have one reason to change.

## No Magic

The platform should never hide important behaviour from users.

## Documentation is Code

Documentation evolves alongside the codebase.

## Tests Protect Architecture

Every business capability should be covered by automated tests.

---

# Definition of Done

A story is complete when:

- Feature implemented
- Tests passing
- Documentation updated
- CLI help reviewed
- Architecture reviewed
- Changelog updated (if applicable)

---

# Commit Convention

Examples

feat(song): create SongService

refactor(cli): modularise command groups

docs(adr): document layered architecture

test(song): add duplicate song tests

---

# Code Review Checklist

- Is the responsibility clear?
- Can this reuse an existing capability?
- Is the architecture still clean?
- Does the documentation still tell the truth?
