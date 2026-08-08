# CreativeOS Roadmap

CreativeOS is being built as a generic campaign operating platform for creators, artists, churches, companies, agencies, organisations, and future client teams.

The architectural rule is simple:

> Specific templates, generic platform.

No single campaign, customer, or industry should define the core. Real campaigns such as music releases are used as proving grounds, while domain-specific behaviour remains configurable through templates and future domain packs.

## Platform Direction

CreativeOS should help a team answer five operational questions continuously:

1. What are we trying to achieve?
2. What work is required?
3. What should happen next?
4. What is blocked or at risk?
5. What did we learn for the next campaign?

The intended platform flow is:

```text
Organisation
    ↓
Project / Initiative
    ↓
Campaign
    ↓
Milestones
    ↓
Actions + Dependencies
    ↓
Execution Planner
    ↓
Campaign Intelligence
    ↓
Content / Deliverables
    ↓
Analytics / Outcomes
    ↓
Campaign Memory
    ↓
AI-assisted Strategy
```

## Core Architectural Boundaries

CreativeOS core should understand generic concepts such as organisations, projects, campaigns, milestones, actions, dependencies, content metadata, assets, outcomes, and intelligence.

Domain-specific behaviour belongs in templates or domain packs.

Examples:

- a music release can define roles such as `teaser`, `performance`, and `social-proof`;
- a church campaign can define roles such as `testimony`, `sermon-clip`, and `event-reminder`;
- a company can define roles such as `case-study`, `product-demo`, and `conversion`;
- a book launch can define roles such as `excerpt`, `author-story`, and `reader-review`.

The core should validate safe structure and lifecycle rules without hard-coding one industry's vocabulary.

## Phase 1 — Platform Foundation

**Status: substantially complete**

Delivered capabilities include:

- organisation discovery and validation;
- project contexts;
- campaign contexts;
- campaign-scoped action persistence;
- safe path isolation;
- action lifecycle states;
- priorities, due dates, channels, dependencies, and milestones;
- repository-native configuration and CLI workflows.

This established the hierarchy:

```text
Organisation → Project → Campaign → Milestone → Action
```

## Phase 2 — Execution Engine

**Status: complete enough for the current product phase**

Delivered capabilities include:

- dependency readiness;
- deterministic execution planning;
- next-action recommendation;
- overdue and ready work views;
- action lifecycle CLI operations;
- reusable execution templates;
- template variables;
- relative date scheduling;
- preview-before-apply behaviour;
- explicit action persistence.

The execution engine remains deterministic. AI must not silently change action order, dependencies, priorities, or campaign state.

## Phase 3 — Milestone and Campaign Intelligence

**Status: complete enough for now**

The intelligence stack currently progresses through:

```text
Progress
    ↓
Health
    ↓
Attention
    ↓
Intervention
    ↓
Campaign Decision Summary
```

This layer interprets execution state without mutating it.

CreativeOS can identify milestone progress, health, attention conditions, advisory interventions, and campaign-level decision summaries while leaving execution ordering under the planner's control.

## Phase 4 — Campaign Start and Orchestration

**Status: complete enough for the current product phase**

The campaign start workflow supports a safer creator-facing path:

```text
campaign start
    ↓
preview campaign
    ↓
--apply
    ↓
create campaign
    ↓
preview recommended execution plan
    ↓
--apply-execution
    ↓
persist campaign actions
```

The implementation was initially proven through a music-release campaign while preserving generic core behaviour.

## Phase 5 — Structured Content Planning

**Status: complete enough for the current product phase**

CreativeOS now models structured content intent rather than treating campaign work as generic publishing tasks.

The content model separates two concerns:

```text
content_role   = why the content exists
content_format = what production form it takes
```

Examples of roles include story, teaser, performance, social proof, release-day, follow-up, testimony, education, case-study, or conversion.

Examples of formats include short-video, static-image, carousel, interview, article, sermon-clip, product-demo, or other domain-defined formats.

Roles and formats remain template-defined rather than universal hard-coded enums.

Delivered capabilities include reusable creative briefs that can carry structured production intent such as objective, audience, message or angle, role, format, channel, call to action, production notes, and approval expectations.

## Phase 6 — Content Inventory and Sequencing

**Status: substantially complete**

CreativeOS can build and inspect campaign content as a structured inventory rather than treating publishing actions independently.

The sequencing model supports intentional variation across dimensions such as:

- role;
- format;
- creative angle;
- channel;
- audience;
- call to action;
- timing.

The goal remains to reduce repetitive campaigns and create intentional content progression over time.

## Phase 7 — Domain Packs

**Status: core capability established**

CreativeOS supports the architectural pattern for reusable domain-specific campaign configuration on top of the generic core.

Candidate and supported directions include:

- music release;
- book launch;
- product launch;
- church event;
- corporate awareness campaign;
- client marketing campaign;
- podcast launch;
- community campaign;
- custom campaign.

A domain pack may define recommended milestones, content roles, content formats, relative scheduling, actions, brief defaults, and expected analytics signals.

Domain-pack expansion should continue incrementally without moving industry vocabulary into the generic core.

## Phase 8 — Asset and Deliverable Tracking

**Status: substantially complete**

CreativeOS tracks campaign deliverables and their production readiness.

Examples include:

- video;
- image;
- caption;
- audio;
- press release;
- document;
- email;
- landing page;
- playlist pitch;
- client approval asset.

Assets support lifecycle concepts including planned, draft, review, approved, and published, along with linkage and location/readiness checks.

The relationship remains:

```text
Action → Creative Brief → Asset / Deliverable
```

## Phase 9 — Operational Campaign Workspace

**Status: substantially complete**

CreativeOS now has a consolidated read-only operating layer for campaign state.

Delivered capabilities include:

- a campaign workspace read model combining content inventory, asset readiness, and execution state;
- a CLI workspace view;
- deterministic operational attention prioritisation;
- a single explainable next-focus recommendation;
- a stable, versioned machine-readable operational snapshot for future API, dashboard, reporting, integration, and agentic consumers.

The underlying services remain interface-independent so CLI, REST API, web, automation, and future agents can reuse the same application logic.

The operational flow now includes:

```text
Campaign Workspace
        ↓
Attention Items
        ↓
Deterministic Priority
        ↓
Next Operational Focus
        ↓
Versioned Operational Snapshot
```

## Phase 10 — Analytics and Outcomes

**Status: NEXT**

CreativeOS should now connect execution with measurable outcomes.

The analytics model must remain generic while allowing domain packs to define relevant metrics.

Possible signals include:

- views;
- engagement;
- clicks;
- shares;
- saves;
- streams;
- conversions;
- registrations;
- attendance;
- sales;
- playlist support;
- radio support;
- campaign-specific business outcomes.

The key question becomes:

> What did we execute, when did we execute it, and what happened afterwards?

The first implementation slices should establish a deterministic, structured outcome model and read services before introducing provider integrations or AI interpretation.

## Phase 11 — Campaign Memory

**Status: planned**

CreativeOS should preserve organisational learning across campaigns.

Campaign memory should retain structured evidence such as:

- execution history;
- blockers and interventions;
- content performance;
- channel performance;
- milestone outcomes;
- timing patterns;
- final campaign results.

This creates institutional memory for creators, teams, organisations, agencies, and clients.

## Phase 12 — Cross-Campaign Learning

**Status: planned**

Once sufficient campaign history exists, CreativeOS should support evidence-based comparison across campaigns.

The system should be able to answer questions such as:

- Which content formats usually perform best?
- Which channels consistently underperform or outperform?
- Which work commonly becomes blocked?
- How early should production begin?
- Which interventions usually restore campaigns to health?
- Which campaign structures are most effective for a given objective?

## Phase 13 — AI-assisted Strategy

**Status: planned**

AI should sit on top of trustworthy structured campaign data rather than replace the deterministic platform.

The intended model is:

```text
Structured campaign state
        +
Historical outcomes
        +
Campaign memory
        ↓
AI interpretation and strategy assistance
```

AI may explain, summarise, suggest, compare, or help generate creative options, but core campaign state must remain traceable to structured data and explicit user actions.

## Phase 14 — Multi-user and Client Operations

**Status: planned**

As CreativeOS expands beyond a single operator, the platform should support team and client workflows such as:

- organisation membership;
- roles and permissions;
- approvals;
- assigned work;
- client review boundaries;
- reusable client campaign templates;
- auditability;
- separation between organisations and projects.

Security and tenant isolation must be designed before broad multi-user adoption.

## Phase 15 — Platform, API, and UI Expansion

**Status: future**

The CLI is the current engineering interface, not the final product boundary.

Core services should remain reusable so CreativeOS can later support:

- web application interfaces;
- REST APIs;
- scheduled automation;
- integrations;
- dashboards;
- external client experiences;
- plugin or extension systems;
- cloud-native deployment and infrastructure as code.

The wider cloud, API, infrastructure, security, and scale-out direction is documented in `docs/PLATFORM_SCALE_OUT.md`.

## Continuous Engineering Tracks

The following are not deferred phases. They run alongside product development.

### Security

Continuously review:

- secret handling;
- repository and file path isolation;
- untrusted YAML and template inputs;
- dependency vulnerabilities;
- GitHub Actions permissions and supply-chain exposure;
- future tenant separation;
- AI/tool integration boundaries.

### Architecture

Continuously protect:

- single responsibility;
- deterministic execution behaviour;
- generic core versus domain-specific configuration;
- explicit write boundaries;
- reusable service interfaces;
- presentation/business-logic separation.

### Quality

Every production slice should maintain:

- tests;
- linting;
- formatting;
- CI health;
- documentation accuracy;
- focused PR scope.

## Current Product Position

CreativeOS has moved beyond a simple productivity CLI into a generic campaign operating platform with deterministic execution, structured content planning, asset readiness, operational attention, and a reusable campaign workspace contract.

The immediate roadmap is:

```text
Template-defined Content Roles          ✅
Template-defined Content Formats        ✅
Creative Brief Model                    ✅
Content Inventory                       ✅
Content Sequencing / Variation          ✅
Domain Pack Foundation                  ✅
Asset / Deliverable Tracking            ✅
Operational Campaign Workspace          ✅
Operational Attention Prioritisation    ✅
Next Operational Focus                  ✅
Operational Snapshot / Export           ✅
Analytics / Outcomes                    NEXT
Campaign Memory
Cross-Campaign Learning
AI-assisted Strategy
Multi-user / Client Operations
Platform / API / UI Expansion
```

The long-term product test is not whether CreativeOS can run one music campaign. It is whether a creator, church, company, agency, or client team can define an objective and use CreativeOS to plan, execute, observe, learn from, and improve a professional campaign without the platform being rewritten for their industry.
