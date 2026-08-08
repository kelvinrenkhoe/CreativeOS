# CreativeOS Platform Scale-Out Strategy

## Purpose

This document records the intended business and technical scale-out direction for CreativeOS so future contributors and AI development agents can make decisions consistently.

CreativeOS is not intended to remain a music-marketing CLI or a single-user content generator. The target is a cloud-native, multi-tenant campaign operating platform for creators, teams, churches, companies, agencies, organisations, and client operations.

The current CLI is an engineering and product-validation interface. It proves the domain model and deterministic application services before those capabilities are exposed through broader platform interfaces.

## Product Direction

The expected business progression is:

```text
Creator productivity tool
        ↓
Team campaign workspace
        ↓
Agency / multi-client operating system
        ↓
Multi-tenant SaaS campaign platform
        ↓
Intelligent campaign operations platform
```

CreativeOS should support multiple industries through a generic core and domain-specific configuration. Music releases are an important proving ground, not the definition of the product.

The core architectural rule remains:

> Specific domain packs and templates, generic platform.

## Business Scale

CreativeOS should be capable of serving four broad operating levels.

### Creator / Individual

A creator, artist, author, consultant, or freelancer can plan and operate campaigns without needing a full marketing team.

### Team / Organisation

A small company, church, artist team, startup, media organisation, or communications team can collaborate around projects, campaigns, content, assets, approvals, and execution.

### Agency / Client Operations

An agency or consultancy can operate multiple client organisations and multiple campaigns while preserving client boundaries, reusable processes, reporting, and governance.

### Enterprise / Platform

Larger organisations can consume CreativeOS through managed interfaces and APIs with stronger identity, audit, security, integration, data-governance, and tenancy requirements.

## Platform Architecture Direction

CreativeOS should evolve toward this boundary:

```text
Users / Clients / Integrations
              │
        Web / Mobile / CLI
              │
            REST API
              │
      Authentication / RBAC
              │
     CreativeOS Application
              │
 ┌────────────┼─────────────┐
 Campaign   Content       Assets
 Services   Services      Services
 └────────────┼─────────────┘
              │
        Persistence Layer
              │
 ┌────────────┼──────────────┐
 Database   Object Store    Cache
              │
       Events / Workers
              │
       External Services
```

The CLI, REST API, web application, future SDKs, and automation interfaces must call the same application services. Business logic must not be duplicated inside presentation or transport layers.

## Modular Monolith First

CreativeOS should not prematurely become a microservices system.

The preferred initial production architecture is a modular monolith with strong internal domain and application boundaries. Services may be separated later when scale, security, ownership, reliability, or deployment characteristics justify doing so.

A future source structure may evolve toward concepts such as:

```text
creativeos/
    domains/
        organisations/
        projects/
        campaigns/
        content/
        assets/
        analytics/

    application/
        services/

    api/
        routes/
        schemas/
        auth/

    infrastructure/
        persistence/
        storage/
        events/

    cli/
```

This is directional, not an instruction to restructure the repository immediately.

## REST API Direction

The REST API should expose the application layer rather than reimplement it.

Likely resource boundaries include:

```text
POST /v1/organisations
POST /v1/organisations/{org}/projects
POST /v1/projects/{project}/campaigns
GET  /v1/campaigns/{campaign}
GET  /v1/campaigns/{campaign}/workspace
GET  /v1/campaigns/{campaign}/attention
GET  /v1/campaigns/{campaign}/next-focus
GET  /v1/campaigns/{campaign}/content
GET  /v1/campaigns/{campaign}/assets
GET  /v1/campaigns/{campaign}/actions
```

These paths are illustrative. API contracts should be versioned, tested, authenticated, authorised, and derived from stable application services.

Existing services such as campaign workspace, attention prioritisation, and next-focus recommendation are intentionally being designed so they can later back API endpoints without being rewritten.

## Cloud and AWS Direction

CreativeOS should ultimately be deployable as a secure cloud-native platform. AWS is the expected primary cloud direction unless a future architecture decision changes that explicitly.

A possible target shape is:

```text
Route 53
   ↓
CloudFront
   ↓
Web Application
   ↓
API Gateway / ALB
   ↓
CreativeOS Application/API
   ↓
PostgreSQL + S3
   ↓
EventBridge / SQS
   ↓
Asynchronous Workers
```

Supporting capabilities may include identity services, KMS, Secrets Manager, CloudWatch, WAF, CloudTrail, backup/recovery controls, and tightly scoped IAM.

Specific AWS services are architectural choices to validate when implementation begins; they are not mandates where a simpler or safer service is more appropriate.

## Infrastructure as Code

Cloud infrastructure must be reproducible and version-controlled. Terraform is the preferred direction for infrastructure as code unless a future ADR deliberately selects another approach.

The infrastructure should eventually support isolated environments such as development, staging, and production, with reusable modules for concerns including networking, application hosting, data, storage, identity, observability, and security.

Infrastructure changes should follow the same review discipline as application changes.

## CI/CD Direction

The current lint-and-test pipelines should evolve with the platform.

A mature delivery flow may include:

```text
Pull Request
    ↓
Lint / Formatting
    ↓
Security and dependency scanning
    ↓
Unit / Integration tests
    ↓
API contract tests
    ↓
Terraform validation / policy checks
    ↓
Build immutable application artifact
    ↓
Deploy development environment
    ↓
Smoke / integration tests
    ↓
Promote to staging
    ↓
Controlled production promotion
```

Production deployment must remain auditable and should not depend on manual console configuration.

## Multi-Tenancy and Security

Multi-tenancy is a product architecture concern, not a future patch.

Before broad multi-user adoption, CreativeOS must establish strong boundaries for:

- organisation and tenant isolation;
- authentication and authorisation;
- role-based access control;
- project and campaign permissions;
- client review boundaries;
- audit trails;
- secret handling;
- encryption in transit and at rest;
- secure object-storage access;
- API abuse protection;
- dependency and supply-chain security;
- backup and recovery;
- data retention and deletion;
- least-privilege cloud IAM.

Current repository path-isolation and explicit-write safeguards should be treated as early foundations of this security posture.

## Data and Persistence

Repository-native persistence is appropriate for the current engineering phase, but it is not assumed to be the final SaaS persistence model.

As the hosted platform develops, transactional application state will likely require a database, while larger creative assets and deliverables should use object storage. The application layer should shield domain logic from the persistence implementation so storage can evolve without rewriting business rules.

## Events and Integrations

External integrations should not be tightly coupled to core campaign logic.

The platform should eventually support event-driven and asynchronous workflows for activities such as publishing, analytics ingestion, notifications, media processing, external approvals, and third-party synchronisation.

Possible integration surfaces include social platforms, email systems, CRM platforms, cloud storage, analytics systems, content-generation services, and customer-owned systems.

Webhooks and APIs should eventually allow enterprise customers to integrate CreativeOS without being required to use the CreativeOS UI.

## Domain Packs and Commercial Expansion

Domain packs are a major scale-out mechanism.

Potential packs include music release, book launch, product launch, church event, corporate campaign, podcast launch, conference, recruitment, fundraising, community, and custom client campaigns.

A future ecosystem may support organisation-owned, partner-built, or marketplace domain packs, provided extension boundaries are secure and versioned.

## Analytics, Memory, and Intelligence

The long-term data chain is:

```text
Campaign intent
    ↓
Planned work
    ↓
Content and assets
    ↓
Execution
    ↓
Channel activity
    ↓
Measured outcomes
    ↓
Campaign memory
    ↓
Cross-campaign learning
```

This structured history should allow CreativeOS to become an operational intelligence system rather than merely a workflow tracker.

## AI and Agentic Direction

Agentic AI is deliberately later in the roadmap.

AI should sit above deterministic CreativeOS services rather than replace them. Future agents should observe structured campaign state, use registered application tools, propose actions, respect permissions and approval boundaries, record auditable decision summaries, and learn from campaign evidence.

The intended principle is:

> AI may decide what appears useful; deterministic CreativeOS services decide what is valid and safe to execute.

The current roadmap must not be derailed to implement autonomous agents prematurely.

## Engineering Tracks

CreativeOS development should be understood as four connected engineering tracks.

### 1. Product and Domain Engine

Campaigns, planning, content, assets, execution, operational workspace, analytics, and memory.

### 2. Platform and API

REST API, authentication, RBAC, tenancy, persistence, integrations, web interfaces, and SDKs.

### 3. Cloud and Infrastructure

AWS architecture, Terraform, environments, CI/CD, observability, resilience, security, backups, and operational controls.

### 4. Intelligence

Analytics, campaign memory, cross-campaign learning, AI assistance, and eventually controlled agentic execution.

These tracks should converge gradually. Cloud or API work should begin when the domain/application boundary is mature enough to expose, rather than replacing the current roadmap prematurely.

## Development Governance and Roles

The project should continue to operate with explicit responsibilities.

The product owner / CEO owns business direction, product priorities, acceptance, and final merge decisions.

The technical architecture and delivery role owns architecture consistency, roadmap execution, repository security, implementation slices, pull-request preparation, test quality, and investigation/fixing of CI failures before presenting work for review.

Future development agents should therefore:

1. inspect current `main`, recent merged PRs, roadmap, and this document before choosing the next architectural slice;
2. preserve generic core versus domain-specific configuration;
3. avoid premature infrastructure, microservice, or AI complexity;
4. keep application services reusable by CLI, API, web, and automation interfaces;
5. protect explicit write boundaries and deterministic behaviour;
6. maintain security as a continuous responsibility;
7. create focused PRs with tests;
8. inspect and fix CI failures without waiting for the product owner to diagnose them;
9. present a PR for review only when its required checks are green;
10. leave final business acceptance and merge approval with the product owner / CEO.

## Immediate Roadmap Rule

This strategy documents the destination; it does not replace the active product roadmap.

Continue the current domain/application roadmap first. Introduce API, cloud infrastructure, multi-tenancy, and agentic capabilities at deliberate architectural milestones rather than allowing them to interrupt foundational campaign capabilities.

The guiding sequence is:

```text
Trustworthy domain engine
        ↓
Stable application services
        ↓
Operational campaign platform
        ↓
Analytics and memory
        ↓
Platform/API and cloud scale-out
        ↓
Multi-user/client maturity
        ↓
AI and controlled agentic operations
```
