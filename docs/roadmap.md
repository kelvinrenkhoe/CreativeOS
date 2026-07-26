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

- [ ] Performance ingestion
- [ ] Campaign measurement
- [ ] Content and visual fatigue signals
- [ ] Recommendation feedback loop
- [ ] Cross-campaign learning

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
| #25 | Image and Poster Planner | Continuity-aware concepts and reusable image formats |\n| #26 | Publishing Adapters | Approval-gated, provider-neutral platform handoff |

## Design principles

1. **Single source of truth** — creative facts are defined once and referenced by stable IDs.
2. **Provider agnostic** — domain models never depend on one AI or publishing provider.
3. **Story before content** — execution is derived from narrative intent.
4. **Memory before repetition** — generation accounts for what already exists.
5. **Creative Universe** — songs, books, video, images, and campaigns share one world.
6. **Human review** — no asset skips from idea to publication without review.
7. **Small, safe PRs** — focused commits, tests, and a deployable `main`.
