# Narrative Timeline

Narrative Timeline turns the ordered beats in a Story Context arc into campaign phases.
It gives downstream campaign, cinematic, book, and social planners a deterministic answer
to which part of the story should be communicated during each week.

## Building a timeline

```python
from core.project import Project
from story import NarrativeTimelineService, StoryContextService

project = Project.discover()
context = StoryContextService(project).build("no-way-back")
timeline = NarrativeTimelineService().build(context, weeks=6)

print(timeline.render())
```

Each story beat becomes one ordered campaign phase. Campaign weeks are distributed as
evenly as possible without changing the narrative order. Any remainder is assigned to
the earliest phases, where setup normally needs more room.

When a Story Context contains multiple arcs, callers must select one explicitly:

```python
timeline = NarrativeTimelineService().build(
    context,
    weeks=6,
    arc_id="journey-home",
)
```

## Boundaries

The timeline is provider agnostic and contains no generated content. It does not decide
platforms, asset formats, publishing dates, or prompts. Those decisions belong to later
campaign and cinematic planners, which can use the active phase's objective as narrative
direction.
