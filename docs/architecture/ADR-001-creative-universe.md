# ADR-001: Creative Universe Foundation

- Status: Accepted
- Date: 2026-07-26

## Context

CreativeOS already separates reusable knowledge, campaign configuration, prompt templates,
AI providers, generated assets, and campaign memory. The next phase must support songs,
books, characters, locations, themes, symbols, and their narrative relationships without
rewriting those existing capabilities.

The system also needs to plan varied cinematic and social content over time. Stable creative
facts must therefore remain separate from campaign strategy and generated execution history.

## Decision

CreativeOS will use three architectural layers:

1. **Creative Universe** — stable, reusable facts and relationships shared across projects.
2. **Creative Strategy** — story arcs, campaign phases, objectives, audiences, timelines,
   and content sequencing for a particular campaign.
3. **Creative Execution** — prompts, captions, videos, images, outreach assets, publishing,
   measurements, and campaign memory.

The Creative Universe is a provider-agnostic domain model. It will not call AI providers,
render prompts, publish content, or store campaign performance.

### Initial domain language

The first implementation defines:

- `Universe`: the root aggregate for a creator's connected body of work.
- `CreativeWork`: a song, book, film, podcast, or other authored work.
- `Character`: a person or narrative identity appearing in the universe.
- `Location`: a real or fictional place.
- `Theme`: a recurring idea such as hope, migration, family, or resilience.
- `Symbol`: a recurring visual or narrative motif such as rain, a passport, or a train.
- `StoryArc`: an ordered narrative progression.
- `Relationship`: a typed link between two universe entities.

All entities use stable string identifiers so YAML files can reference one another without
embedding duplicate facts.

### Ownership boundaries

| Information | Owner |
|---|---|
| Artist biography and verified facts | Knowledge |
| Works, characters, themes, symbols, locations, relationships | Creative Universe |
| Campaign goal, phase, audience, schedule, and narrative sequence | Creative Strategy |
| Generated copy, prompt output, video plans, and publishing state | Creative Execution |
| Previously generated campaign assets | Campaign Memory |
| Performance results and recommendations | Analytics and Learning |

### Dependency direction

```text
Knowledge ──────┐
                ▼
        Creative Universe
                │
                ▼
        Creative Strategy
                │
                ▼
        Creative Execution
                │
                ▼
      Analytics and Learning
```

Lower layers may consume data from layers above them. The Creative Universe must not depend
on campaign generation, prompt templates, providers, publishing, or analytics.

### File direction

A workspace will eventually be able to represent the universe with structured YAML:

```text
universe/
├── universe.yaml
├── works/
├── characters/
├── locations/
├── themes/
├── symbols/
└── arcs/
```

PR #16 establishes the Python domain model first. Loading, validation, knowledge enrichment,
story context, timelines, and AI integrations will follow behind separate services and
reviewable pull requests.

## Consequences

### Positive

- Existing campaign and knowledge architecture remains intact.
- Songs and books can share characters, locations, themes, and symbols.
- Video providers can be added later as adapters rather than domain dependencies.
- Stable identifiers prevent repeated creative facts from drifting across campaigns.
- Campaign timelines can track novelty without polluting universe facts.

### Trade-offs

- References require resolution and validation.
- The universe schema must evolve carefully as new creator types are supported.
- Campaign memory and universe knowledge remain separate even when both inform generation.

## Guardrails

- One creative fact should have one authoritative home.
- Models contain data and invariants, not provider or filesystem behaviour.
- Provider-specific prompt fields do not belong in the domain model.
- Campaign dates, CTAs, posting cadence, and performance metrics do not belong in the
  Creative Universe.
- New entity types should be added only when generic works and typed relationships cannot
  represent the requirement clearly.
