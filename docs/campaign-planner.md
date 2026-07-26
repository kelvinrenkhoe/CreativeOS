# Objective-Driven Campaign Planner

The Campaign Planner combines a resolved Story Context, its Narrative Timeline, and
human-supplied campaign intent into one provider-agnostic plan. It establishes what the
campaign is trying to achieve, who it is for, how it should feel, where it will run, and
which narrative objective guides each phase.

## Building a plan

```python
from core.project import Project
from services.campaign_planner import CampaignPlannerService
from story import NarrativeTimelineService, StoryContextService

project = Project.discover()
context = StoryContextService(project).build("no-way-back")
timeline = NarrativeTimelineService().build(context, weeks=6)

plan = CampaignPlannerService().build(
    context,
    timeline,
    objective="Grow discovery and meaningful streams",
    audience="Afrobeats listeners who value migration stories",
    tone="Cinematic, honest, and hopeful",
    platforms=("instagram", "tiktok", "youtube"),
)

print(plan.render())
```

Every timeline phase becomes a `CampaignPhaseDirection`. The phase preserves its
narrative objective while inheriting the overall campaign objective, audience, tone, and
normalized platform list. Callers can use `direction_for_week()` to select the active
direction for daily recommendations and future asset planners.

## Boundaries

The planner is deterministic and provider agnostic. It does not generate captions,
images, videos, prompts, or publishing schedules. Asset Intelligence remains responsible
for assessing proposed content against campaign memory. Later generators can consume the
typed `CampaignPlan`, create candidate assets, and use Asset Intelligence before asking
a human to review them.
