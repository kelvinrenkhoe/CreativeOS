# 🎨 CreativeOS

> **The Open Source Operating System for Creators**

CreativeOS is an open-source platform that helps creators manage their entire creative workflow—from idea to audience—with AI-assisted automation, reusable templates, and structured project management.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)]()
[![Status](https://img.shields.io/badge/status-Active%20Development-green.svg)]()

---

# What is CreativeOS?

CreativeOS provides a structured, repeatable workflow for creators to plan, create, organize, promote, and maintain their creative work.

Instead of juggling dozens of disconnected applications, CreativeOS acts as the orchestration layer that brings projects, AI, content generation, and marketing together in a single workspace.

Whether you're a musician, author, podcaster, YouTuber, educator, or independent creator, CreativeOS helps you build a consistent creative system that scales.

---

# The Problem

Modern creators often rely on many disconnected tools:

- ChatGPT
- Canva
- CapCut
- Spotify for Artists
- Google Drive
- Notion
- Social Media Platforms
- Analytics Dashboards

Each tool solves one part of the creative process, but none manages the complete creative lifecycle.

This often leads to:

- duplicated work
- inconsistent branding
- forgotten marketing tasks
- scattered project files
- repetitive prompting
- inefficient workflows

---

# The Solution

CreativeOS becomes the orchestration layer.

```text
Idea
 │
 ▼
Planning
 │
 ▼
Writing
 │
 ▼
AI Generation
 │
 ▼
Editing
 │
 ▼
Publishing
 │
 ▼
Promotion
 │
 ▼
Analytics
 │
 ▼
Archive
```

One workflow.

One repository.

One operating system for creators.

---

# Philosophy

Creators should spend more time creating and less time managing.

CreativeOS automates repetitive work while keeping creative decisions in the hands of the creator.

The project applies software engineering principles—including version control, reusable components, automation, testing, and documentation—to the creative process.

---

# Features

## Available

- ✅ Workspace Initialization
- ✅ Campaign Management
- ✅ AI Provider Framework
- ✅ OpenAI Provider Integration
- ✅ Prompt Template Engine
- ✅ Markdown Prompt Library
- ✅ Campaign Asset Generation
- ✅ CLI Interface
- ✅ Comprehensive Unit Test Suite

## In Development

- Artist Knowledge Base
- Song Library Management
- Book Projects
- AI Image Workflows
- AI Video Workflows
- Spotify Integration
- Analytics Dashboard
- Plugin Architecture
- Creator Templates

---

# Example Commands

```bash
creativeos init

creativeos doctor

creativeos status

creativeos new-song "No Lose Guard"

creativeos new-campaign "Now Them Go Hear Me"

creativeos generate-campaign "Now Them Go Hear Me"

creativeos ai providers

creativeos ai test

creativeos analytics
```

---

# Repository Structure

```text
CreativeOS/
│
├── ai/
│   ├── manager.py
│   ├── mock.py
│   ├── openai_provider.py
│   ├── provider.py
│   └── registry.py
│
├── cli/
│
├── core/
│
├── prompts/
│   ├── instagram.md
│   ├── facebook.md
│   ├── tiktok.md
│   ├── x.md
│   ├── playlist_pitch.md
│   ├── radio_pitch.md
│   ├── press_release.md
│   └── content_calendar.md
│
├── services/
│   ├── campaign.py
│   ├── campaign_generator.py
│   └── prompt_template.py
│
├── tests/
│
├── docs/
│
├── scripts/
│
├── pyproject.toml
│
└── README.md
```

---

# Prompt Templates

CreativeOS stores AI prompts as Markdown templates inside the **`prompts/`** directory.

Instead of embedding prompts directly in Python code, each campaign asset has its own reusable Markdown template.

## Prompt Architecture

```text
CampaignGeneratorService
        │
        ▼
PromptTemplateService
        │
        ▼
prompts/*.md
        │
        ▼
Placeholder Rendering
        │
        ▼
AI Provider
        │
        ▼
Generated Campaign Assets
```

The prompt engine keeps prompt content separate from application logic, making prompts easy to review, update, and improve without modifying Python code.

## Template Placeholders

Templates use lightweight placeholder variables.

Example:

```text
Campaign: {{ campaign }}
Artist: {{ artist }}
Genre: {{ genre }}
Purpose: {{ purpose }}
```

During campaign generation these placeholders are automatically replaced with values from the campaign manifest before the prompt is sent to the configured AI provider.

Supported placeholders include:

| Placeholder | Description |
|-------------|-------------|
| `{{ campaign }}` | Campaign or release name |
| `{{ artist }}` | Artist name |
| `{{ genre }}` | Artist genre |
| `{{ purpose }}` | Purpose of the generated asset |
| `{{ release_date }}` | Release date |
| `{{ spotify }}` | Spotify link |
| `{{ smart_link }}` | Smart link |
| `{{ hashtags }}` | Campaign hashtags |
| `{{ platforms }}` | Target platforms |
| `{{ goals }}` | Campaign goals |
| `{{ audience }}` | Target audience |
| `{{ tone }}` | Desired writing tone |
| `{{ objective }}` | Marketing objective |

## Adding a New Campaign Asset

Adding a new AI-generated content type is straightforward:

1. Create a new Markdown template inside the `prompts/` directory.
2. Register a matching `CampaignAsset` in `services/campaign_generator.py`.
3. Run the test suite.

```bash
ruff check .
pytest
```

This design keeps the prompt engine simple while allowing more advanced template engines to be introduced in the future without changing the public API.

---


# Artist Knowledge Base

CreativeOS separates reusable artist knowledge from individual campaign data.

Instead of repeating biographies, achievements, brand messaging, audience
information, quotes, and song details in every campaign manifest, CreativeOS
loads this information from Markdown documents in the `knowledge/` directory.

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

## How it works

```text
campaign.yaml
        │
        ├──────────────┐
        ▼              │
KnowledgeService       │
        │              │
        ▼              │
Aggregated Context ◄───┘
        │
        ▼
PromptTemplateService
        │
        ▼
Rendered Prompt
        │
        ▼
AI Provider
```

`KnowledgeService` loads the available top-level documents and can also include
song-specific knowledge based on the campaign name.

For example, a campaign named `No Break` automatically checks for:

```text
knowledge/songs/no-break.md
```

The aggregated context is supplied to prompt templates through:

```text
{{ knowledge }}
```

When no additional knowledge is available, campaign generation continues using
a safe fallback message.

## Benefits

- Maintains one source of truth for artist information
- Produces more consistent and brand-aware AI content
- Automatically includes campaign-specific song knowledge
- Avoids duplicating information across campaign manifests
- Supports dependency injection for testing and future integrations
- Makes future features such as EPKs, media kits, press outreach, and blog
  generation easier to build

## Adding knowledge

Update the existing Markdown documents with verified artist information.

To add knowledge for another song, create a file using the slugified song title:

```text
knowledge/songs/song-title.md
```

Keep information factual and current because it may be reused across every
AI-generated campaign asset.

# AI Architecture

CreativeOS uses a provider-based architecture.

```text
Campaign Generator
        │
        ▼
Prompt Template Engine
        │
        ▼
AI Provider Interface
        │
        ├──────── Mock Provider
        │
        └──────── OpenAI Provider
```

This abstraction allows multiple AI providers to be supported while keeping the rest of the application unchanged.

---

# Testing

CreativeOS follows a test-first approach wherever practical.

The project currently includes comprehensive unit and integration tests covering:

- Campaign management
- Prompt template rendering
- AI provider framework
- Campaign generation
- CLI behaviour
- Template integration

Run the complete test suite:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

Format the project:

```bash
ruff format .
```

---

# Project Status

**Current Phase**

> Sprint 2 — Core AI Platform

## Completed

- Workspace initialization
- Campaign management
- AI provider abstraction
- OpenAI provider integration
- Prompt template engine
- AI campaign generation
- Unit and integration testing

## Current Focus

- Artist Knowledge Base
- Context-aware prompt generation
- Plugin architecture
- AI workflow expansion

---

# Design Principles

- Creator First
- Documentation First
- Open Source Core
- Test Driven Development
- Separation of Concerns
- AI Assisted
- Platform Agnostic
- Automation Where It Matters

---

# Who is CreativeOS for?

CreativeOS is designed for:

- Musicians
- Authors
- Podcasters
- YouTubers
- Educators
- Independent Creators
- Creative Teams

---

# Roadmap

## Version 0.2 ✅

- Workspace Initialization

## Version 0.3 ✅

- Campaign Management

## Version 0.4 ✅

- AI Provider Framework

## Version 0.5 ✅

- Prompt Template Engine

## Version 0.6 (Current)

- Artist Knowledge Base
- Context Engine
- Prompt Optimization
- Expanded AI Workflows

## Version 1.0

- Stable Public Release
- Plugin Ecosystem
- Creator Marketplace
- Community Templates
- Multi-provider AI Support

---

# Contributing

CreativeOS is an open-source project.

Contributions of every kind are welcome, including:

- Code
- Documentation
- Prompt templates
- Bug reports
- Feature requests
- Integrations
- Testing
- Examples

Please ensure all tests pass before submitting a pull request.

```bash
ruff check .
pytest
```

---

# Inspiration

CreativeOS is inspired by the discipline of software engineering and the realities of independent creators.

The project brings together proven engineering practices—automation, reusable templates, version control, testing, structured workflows, and AI—to help creators spend less time managing work and more time creating it.

---

# License

MIT License

See the `LICENSE` file for details.

---

> **Build Less Chaos. Create More.**
