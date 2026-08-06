# 🎨 CreativeOS

> **The AI Marketing Operating System for Independent Creators**

**Plan smarter. Create better. Launch stronger.**

CreativeOS is an open-source, AI-powered marketing operating system that helps independent creators plan campaigns, generate content, create video strategies, organise releases, analyse performance, and learn from every launch.

Whether you are releasing a song, publishing a book, launching a podcast, growing a personal brand, or promoting another creative project, CreativeOS acts as your AI marketing team—helping you decide what to create, when to publish it, and why it matters.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)]()
[![Status](https://img.shields.io/badge/status-Active%20Development-green.svg)]()

---

## Why CreativeOS Exists

Independent creators rarely struggle because they lack creativity.

They struggle because marketing is fragmented.

Launching creative work often means switching between disconnected tools for:

- campaign planning
- AI writing
- video concepts
- design and editing
- publishing schedules
- project management
- social media promotion
- analytics and reporting

This creates duplicated work, inconsistent branding, repetitive prompting, scattered assets, missed opportunities, and creative burnout.

Creators end up spending more time managing marketing than creating.

CreativeOS brings the complete marketing lifecycle into one intelligent platform.

```text
Campaign Strategy
        │
        ▼
Content Creation
        │
        ▼
Video Direction
        │
        ▼
Publishing Operations
        │
        ▼
Campaign Intelligence
        │
        ▼
Learning
```

Every campaign should make the next one smarter.

---

## What Makes CreativeOS Different

Traditional AI tools generate isolated pieces of content.

CreativeOS manages complete campaigns.

| Traditional AI | CreativeOS |
|----------------|------------|
| Generates text | Manages complete campaigns |
| Responds one prompt at a time | Recommends the next useful action |
| Produces generic outputs | Uses creator and campaign context |
| Forgets previous releases | Builds persistent campaign knowledge |
| Focuses on content | Focuses on outcomes |
| Reacts to requests | Supports daily campaign execution |

CreativeOS is not another AI writing assistant.

It is an AI Marketing Operating System.

---

## The Creator Workflow

CreativeOS is designed around the way creators actually plan and execute releases.

### 🎯 Plan

Create a structured campaign strategy, define objectives, and organise the rollout.

```bash
creativeos campaign ai-plan "No Lose Guard"
```

### 🎬 Create

Generate campaign-ready creative direction and content.

```bash
creativeos generate-campaign "No Lose Guard"
```

Future creative workflows include:

```bash
creativeos caption generate "No Lose Guard"
creativeos video generate "No Lose Guard"
creativeos image generate "No Lose Guard"
```

### 🚀 Launch

Coordinate publishing, campaign milestones, release checklists, and daily actions.

### 📈 Measure

Track campaign health, momentum, platform balance, readiness, and performance.

### 🧠 Learn

Build reusable campaign knowledge from successful captions, hooks, posting patterns, assets, and release decisions.

---

## Core Capabilities

### 🎯 Campaign Intelligence

CreativeOS helps creators plan and organise complete campaigns.

Current and planned capabilities include:

- AI campaign planning
- campaign management
- objectives and milestones
- campaign calendars
- daily priorities
- release timelines
- launch readiness

### 🎬 Creative Intelligence

CreativeOS is being developed as a video-first content system for modern creator marketing.

Planned creative packages include:

- video concepts
- storyboards
- shot lists
- hooks
- scripts
- voice-over ideas
- captions
- on-screen text
- editing notes
- thumbnail prompts
- image prompts

The goal is not only to generate content, but to tell creators what to make, how to make it, and how it supports the campaign.

### 📊 Campaign Operations and Analytics

CreativeOS coordinates the work required to move a campaign from plan to audience.

Capabilities include or will include:

- campaign asset generation
- structured project workspaces
- publishing calendars
- release checklists
- analytics refreshes
- campaign health
- performance reports
- recommendations

### 🧠 Campaign Memory

CreativeOS separates reusable creator knowledge from individual campaign data.

Over time, the platform is designed to remember:

- creator identity and brand positioning
- campaign-specific knowledge
- successful content patterns
- effective hooks and captions
- preferred platforms and formats
- high-performing release strategies

This enables future campaigns to become more personalised and informed.

---

## Who CreativeOS Is For

CreativeOS is designed for independent creators and small creative teams, including:

- 🎵 musicians
- 📚 authors
- 🎙️ podcasters
- 🎥 filmmakers
- 📱 content creators
- 🎤 speakers
- 🎓 educators
- 🚀 entrepreneurs

The long-term platform can also support creative agencies, record labels, publishers, studios, and marketing teams.

---

## Product Vision

CreativeOS is built around one belief:

> Independent creators should spend less time managing marketing and more time creating exceptional work.

Rather than replacing creativity, CreativeOS provides the structure, automation, campaign intelligence, and AI assistance needed to help creators consistently launch and grow their work.

The CLI is the first interface, not the final product.

The same core capabilities can later support:

- web applications
- desktop applications
- mobile applications
- APIs
- background workers
- automations
- third-party integrations

---

## Current Development Focus

CreativeOS is being developed and validated through real creator workflows rather than hypothetical use cases.

The current product focus is moving from core AI infrastructure into creator-facing capabilities:

- provider-backed AI campaign planning
- reusable prompt construction
- structured AI validation
- caption generation
- video direction
- campaign calendars
- daily briefs
- campaign health
- recommendations

Every feature should help a creator plan, create, launch, measure, or improve a campaign.

---

## Available Today

- ✅ Workspace initialization
- ✅ Campaign management
- ✅ AI provider framework
- ✅ OpenAI provider integration
- ✅ Mock provider for deterministic development
- ✅ Prompt template engine
- ✅ Markdown prompt library
- ✅ Reusable prompt builder
- ✅ Provider-backed AI campaign planning
- ✅ Campaign asset generation
- ✅ Artist knowledge base
- ✅ Campaign memory foundations
- ✅ Runtime locking, retries, checkpoints, and history
- ✅ Background campaign worker foundations
- ✅ CLI interface
- ✅ Comprehensive unit and integration test suite

## In Active Development

- AI caption generation
- AI video direction
- image prompt generation
- content calendar generation
- daily creator brief
- campaign health scoring
- recommendation engine
- launch readiness
- analytics integrations
- publishing workflows

---

## Example Commands

Initialise and inspect a workspace:

```bash
creativeos init
creativeos doctor
creativeos status
```

Create and manage projects:

```bash
creativeos new-song "No Lose Guard"
creativeos new-campaign "No Lose Guard"
creativeos generate-campaign "No Lose Guard"
```

Use AI capabilities:

```bash
creativeos ai providers
creativeos ai test
creativeos campaign ai-plan "No Lose Guard"
```

Inspect campaign execution:

```bash
creativeos campaign history "campaign-id"
creativeos worker status
creativeos worker run-once
```

Review analytics:

```bash
creativeos analytics
```

> Command names evolve as the product grows. Run `creativeos --help` and the relevant command group's `--help` output for the current CLI contract.

---

## Architecture

CreativeOS is designed as a set of reusable product capabilities rather than a CLI-only application.

```text
CLI / Future Web / Future Mobile / Worker
                  │
                  ▼
             Public APIs
                  │
                  ▼
        Campaign and Creative Services
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  Prompt Framework      Runtime Platform
        │                   │
        ▼                   ▼
   AI Providers      History / Retry / Locks
```

### AI Provider Architecture

CreativeOS uses a provider-based AI architecture.

```text
Campaign or Content Service
            │
            ▼
      Prompt Framework
            │
            ▼
    AI Provider Interface
            │
     ┌──────┴──────┐
     ▼             ▼
Mock Provider   OpenAI Provider
```

This abstraction allows providers to change without rewriting campaign and content services.

### Prompt Architecture

CreativeOS supports both reusable Markdown templates and deterministic section-based prompt construction.

```text
Campaign / Content Service
            │
     ┌──────┴──────┐
     ▼             ▼
PromptBuilder  PromptTemplateService
     │             │
     └──────┬──────┘
            ▼
       AI Provider
            ▼
   Validated Structured Output
```

This keeps prompt content separate from business logic and makes AI behaviour easier to test, review, and improve.

---

## Repository Structure

The project is organised around AI providers, CLI interfaces, core project models, reusable services, runtime infrastructure, prompts, knowledge, and tests.

```text
CreativeOS/
├── ai/                 # AI providers, manager, registry, and prompt framework
├── api/                # Reusable application-facing APIs
├── cli/                # Typer command groups and Rich rendering
├── core/               # Workspace and project foundations
├── knowledge/          # Reusable creator and project knowledge
├── prompts/            # Markdown prompt templates
├── services/           # Campaign, content, analytics, memory, and runtime services
├── tests/              # Unit and integration tests
├── docs/               # Product and engineering documentation
├── scripts/            # Development and operational utilities
├── pyproject.toml
└── README.md
```

The exact file structure evolves as capabilities mature. The repository itself remains the source of truth.

---

## Prompt Templates

CreativeOS stores reusable AI prompts as Markdown templates inside the `prompts/` directory.

Instead of embedding every prompt directly in Python code, campaign assets can use versioned templates that are easy to review and improve.

Templates support lightweight placeholder variables such as:

```text
Campaign: {{ campaign }}
Artist: {{ artist }}
Genre: {{ genre }}
Purpose: {{ purpose }}
Knowledge: {{ knowledge }}
```

Common placeholders include:

| Placeholder | Description |
|-------------|-------------|
| `{{ campaign }}` | Campaign or release name |
| `{{ artist }}` | Creator or artist name |
| `{{ genre }}` | Genre or category |
| `{{ purpose }}` | Purpose of the generated asset |
| `{{ release_date }}` | Release date |
| `{{ platforms }}` | Target platforms |
| `{{ goals }}` | Campaign goals |
| `{{ audience }}` | Target audience |
| `{{ tone }}` | Desired tone |
| `{{ objective }}` | Marketing objective |
| `{{ knowledge }}` | Aggregated creator and campaign knowledge |

To add a template-backed campaign asset:

1. Create a Markdown template inside `prompts/`.
2. Register the matching campaign asset in the relevant service.
3. Add focused tests.
4. Run linting and the test suite.

---

## Creator Knowledge Base

CreativeOS separates reusable creator knowledge from individual campaign data.

The `knowledge/` directory can contain verified information such as:

```text
knowledge/
├── artist.md
├── biography.md
├── brand.md
├── achievements.md
├── audiences.md
├── media-kit.md
├── quotes.md
└── songs/
    ├── carry-your-name.md
    ├── no-break.md
    └── ...
```

A campaign can combine its manifest with relevant knowledge before rendering a prompt.

This approach:

- maintains one source of truth
- improves brand consistency
- avoids repeating information across campaigns
- enables campaign-specific context
- supports future media kits, outreach, articles, and reports

Knowledge should remain factual and current because it may be reused across many generated assets.

---

## Testing and Quality

CreativeOS follows a test-first approach wherever practical.

The test suite covers areas including:

- workspace and campaign management
- prompt rendering
- AI provider behaviour
- structured response validation
- campaign generation
- campaign memory
- analytics
- runtime execution and recovery
- CLI behaviour

Run linting:

```bash
ruff check .
```

Check formatting:

```bash
ruff format --check .
```

Apply formatting:

```bash
ruff format .
```

Run the complete test suite:

```bash
pytest
```

---

## Design Principles

- **Creator first** — Every capability should help creators release better work.
- **Campaign first** — Content should support a measurable campaign objective.
- **Video first** — Modern creator marketing depends heavily on short-form video.
- **Open-source core** — The platform should remain extensible and transparent.
- **AI assisted, creator controlled** — AI accelerates decisions without replacing creative ownership.
- **Separation of concerns** — Interfaces, services, prompts, providers, and persistence remain modular.
- **Test driven** — Important behaviour should be protected by focused tests.
- **Platform agnostic** — Core capabilities should work beyond the CLI.
- **Automation where it matters** — Automate repetitive work while preserving judgment and authenticity.
- **Learn from every campaign** — Campaign history should improve future recommendations.

---

## Roadmap

### Phase 1 — AI and Campaign Foundations

- ✅ Workspace and campaign management
- ✅ AI provider framework
- ✅ prompt templates and shared prompt construction
- ✅ creator knowledge base
- ✅ provider-backed AI campaign planning
- ✅ runtime reliability and worker foundations

### Phase 2 — Creative Intelligence

- AI caption generation
- AI video direction
- storyboards and shot lists
- hooks and scripts
- image and thumbnail prompts

### Phase 3 — Campaign Operations

- content calendars
- daily creator brief
- release checklists
- launch readiness
- campaign health
- recommendation engine

### Phase 4 — Analytics and Learning

- platform analytics integrations
- performance trends
- campaign memory
- high-performing content analysis
- personalised recommendations

### Phase 5 — Autonomous Marketing Operations

- publishing integrations
- scheduled campaign workflows
- automated daily briefs
- proactive campaign monitoring
- web, desktop, and mobile interfaces

---

## Contributing

CreativeOS is an open-source project, and contributions are welcome in areas such as:

- code
- documentation
- prompt templates
- bug reports
- feature requests
- integrations
- tests
- examples
- creator workflow research

Before submitting a pull request, run:

```bash
ruff check .
ruff format --check .
pytest
```

Contributors should understand the product direction before introducing major capabilities:

> CreativeOS exists to help independent creators plan, create, launch, measure, and improve their marketing campaigns.

---

## Mission

Help independent creators spend less time managing marketing and more time creating exceptional work.

## Vision

Become the AI Marketing Operating System that independent creators rely on to consistently launch and grow their creative work.

---

## License

CreativeOS is available under the MIT License.

See the [`LICENSE`](LICENSE) file for details.

---

> **Plan smarter. Create better. Launch stronger.**
