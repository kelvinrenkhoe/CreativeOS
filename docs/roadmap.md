# CreativeOS Product Roadmap

CreativeOS evolves through small, independently mergeable capabilities. Each pull request
must keep `main` deployable and include focused tests for new behaviour.

## Phase 1 — Campaign Foundation

- [x] Workspace and repository model
- [x] Campaign management
- [x] AI provider abstraction
- [x] Prompt template engine
- [x] Campaign asset generation
- [x] Artist knowledge base
- [x] Campaign memory

## Phase 2 — Creative Universe

- [x] Creative Universe domain models
- [x] YAML loading and reference validation
- [x] Knowledge enrichment
- [x] Story-context rendering
- [x] Narrative timeline and campaign phases
- [x] Asset novelty and repetition checks

## Phase 3 — AI Creative Director

- [x] Objective-driven campaign planner
- [x] Daily `creativeos next` recommendations
- [x] Cinematic treatment and storyboard planner
- [x] Provider-agnostic video prompt model
- [x] Image and poster planner
- [x] Publishing adapters

## Phase 4 — Analytics and Learning

- [x] Performance ingestion
- [x] Campaign measurement
- [x] Content and visual fatigue signals
- [x] Recommendation feedback loop
- [x] Cross-campaign learning

## Phase 5 — Campaign Operations

- [x] Approval-gated campaign orchestration
- [x] Persistent campaign run state
- [x] Provider execution adapters
- [x] Campaign scheduling and queueing
- [ ] Operations dashboard and audit history

## Planned pull requests

| PR | Capability | Outcome |
|---|---|---|
| #16 | Creative Universe Foundation | Domain language and invariants |
| #17 | Universe Service | YAML loading and reference resolution |
| #18 | Story Context | Knowledge-enriched reusable story context |
| #19 | Narrative Timeline | Sequenced, phase-aware campaign planning |
| #20 | Asset Intelligence | Novelty scoring and repetition controls |
| #21 | Campaign Planner | Objective, audience, tone, platform, and phase direction |
| #22 | Daily Recommendations | Phase-aware `creativeos next` recommendations |
| #23 | Cinematic Planner | Treatments, scenes, shots, and provider-neutral direction |
| #24 | Video Prompt Model | Provider-agnostic prompts derived from cinematic treatments |
| #25 | Image and Poster Planner | Continuity-aware concepts and reusable image formats |
| #26 | Publishing Adapters | Approval-gated, provider-neutral platform handoff |
| #27 | Performance Ingestion | Normalized, provider-neutral performance observations |
| #28 | Campaign Measurement | Campaign-level metric summaries and comparisons |
| #29 | Fatigue Signals | Content, visual, and performance fatigue indicators |
| #30 | Recommendation Feedback Loop | Evidence-based, human-reviewed strategy adjustments |
| #32 | Cross-Campaign Learning | Reusable patterns from completed campaign evidence |
| #33 | Campaign Orchestration | Approval-gated end-to-end campaign lifecycle |
| #35 | Persistent Campaign Run State | Versioned save and resume of lifecycle progress |
| #36 | Provider Execution Adapters | Approval-gated image and video provider execution |
| #37 | Campaign Scheduling and Queueing | Ordered, duplicate-safe approved execution work |

## Design principles

1. **Single source of truth** — creative facts are defined once and referenced by stable IDs.
2. **Provider agnostic** — domain models never depend on one AI or publishing provider.
3. **Story before content** — execution is derived from narrative intent.
4. **Memory before repetition** — generation accounts for what already exists.
5. **Creative Universe** — songs, books, video, images, and campaigns share one world.
6. **Human review** — no asset skips from idea to publication without review.
7. **Small, safe PRs** — focused commits, tests, and a deployable `main`.
