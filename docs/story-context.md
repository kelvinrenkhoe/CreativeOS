# Story Context

Story Context turns one Creative Universe work into a resolved, reusable narrative input.
It keeps downstream campaign, timeline, cinematic, book, and social planners independent
from YAML structure and AI providers.

## Building context

```python
from core.project import Project
from story import StoryContextService

project = Project.discover()
context = StoryContextService(project).build("no-lose-guard")

print(context.render())
```

The context contains:

- the selected creative work;
- its referenced themes, characters, locations, and symbols;
- story arcs directly connected to the work by universe relationships;
- relationships between the selected story elements;
- available artist, brand, audience, and work knowledge.

The structured `StoryContext` object should be preferred by application services.
Its deterministic Markdown rendering is available for prompts, debugging, exports, and
other text consumers.

## Boundaries

`UniverseService` remains responsible for loading and validating `universe.yaml`.
`StoryContextService` resolves a work's relevant narrative subgraph and enriches it
through `KnowledgeService`. It does not generate content, call an AI provider, schedule
campaign phases, or mutate the Creative Universe.
