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
- [x] Operations dashboard and audit history

## Phase 6 — Production Integrations

- [x] Controlled queue worker
- [x] Persistent queue and worker leases
- [x] Provider credential and configuration boundary
- [x] Real image provider adapter
- [x] Real video provider adapter
- [x] Production publishing adapter
- [x] Analytics ingestion connectors

## Phase 7 — Autonomous Campaign Runtime

- [x] Campaign runtime coordinator
- [x] Persistent runtime checkpoints
- [x] Human review inbox
- [x] Publication reconciliation
- [x] Scheduled analytics refresh
- [x] Evidence-based campaign adaptation

The runtime connects existing campaign services one safe action at a time. It must
preserve explicit human approval, never infer publication success after an uncertain
provider response, and never change campaign strategy without reviewable evidence.

## Phase 8 — Live Campaign Operations

- [x] Read-only campaign runtime status CLI
- [x] One-action campaign runtime CLI
- [x] Durable human review decisions
- [x] Campaign human review CLI
- [ ] Unified campaign operations dashboard
- [ ] Content schedule execution
- [ ] Operator notifications and weekly reports

This phase exposes the autonomous runtime through safe operator workflows. Status
inspection remains read-only, while mutation commands assemble durable queue, audit,
checkpoint, and provider state explicitly.

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
| #38 | Operations Dashboard and Audit History | Unified read model and attributable operational events |
| #39 | Controlled Queue Worker | Approval-preserving execution with retries and audit evidence |
| #40 | Persistent Queue and Worker Leases | Durable queue recovery and exclusive expiring work ownership |
| #41 | Provider Credential and Configuration Boundary | Secret-safe capability configuration |
| #42 | Real OpenAI Image Provider Adapter | Approved image execution through OpenAI |
| #43 | Real Runway Video Provider Adapter | Approved cinematic video execution through Runway |
| #44 | Production Instagram Publishing Adapter | Human-approved image and Reel publication |
| #45 | Instagram Analytics Ingestion Connector | Read-only media insights normalized for campaign learning |
| #46 | Campaign Runtime Coordinator | One-action campaign advancement with preserved human-review gates |
| #47 | Persistent Runtime Checkpoints | Restart-safe action fencing without duplicate provider execution |
| #48 | Human Review Inbox | Unified, attributable decisions across campaign review gates |
| #49 | Publication Reconciliation | Read-only provider evidence for uncertain publication attempts |
| #50 | Scheduled Analytics Refresh | Durable recurring analytics collection with deterministic windows and restart-safe attempt fencing |
| #51 | Evidence-Based Campaign Adaptation | Reviewable strategy recommendations derived from preserved campaign evidence |
| #54 | Campaign Runtime Status CLI | Read-only persisted stage, evidence, and next-requirement inspection |
| #56 | Campaign Runtime Run CLI | One safe persisted runtime action per operator invocation |
| #59 | Durable Human Review Decisions | Restart-safe, attributable, idempotent review decisions |
| #58 | Campaign Human Review CLI | Campaign-scoped listing and one attributable decision per invocation |

## Design principles

1. **Single source of truth** — creative facts are defined once and referenced by stable IDs.
2. **Provider agnostic** — domain models never depend on one AI or publishing provider.
3. **Story before content** — execution is derived from narrative intent.
4. **Memory before repetition** — generation accounts for what already exists.
5. **Creative Universe** — songs, books, video, images, and campaigns share one world.
6. **Human review** — no asset skips from idea to publication without review.
7. **Small, safe PRs** — focused commits, tests, and a deployable `main`.
