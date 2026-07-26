# Cinematic Planner

The Cinematic Planner converts a resolved Story Context and objective-driven Campaign
Plan into a provider-agnostic visual treatment. Each campaign phase becomes one scene
with a narrative purpose, setting, subjects, recurring motifs, mood, and a three-shot
visual sequence.

## Building a treatment

```python
from core.project import Project
from services.campaign_planner import CampaignPlannerService
from services.cinematic_planner import CinematicPlannerService
from story import NarrativeTimelineService, StoryContextService

project = Project.discover()
context = StoryContextService(project).build("no-way-back")
timeline = NarrativeTimelineService().build(context, weeks=6)
campaign = CampaignPlannerService().build(
    context,
    timeline,
    objective="Grow discovery and meaningful streams",
    audience="Afrobeats listeners who value migration stories",
    tone="Cinematic, honest, and hopeful",
    platforms=("instagram", "tiktok", "youtube"),
)

treatment = CinematicPlannerService().build(context, campaign)
print(treatment.render())
```

The planner grounds scenes in known universe locations, characters, symbols, and themes.
Locations rotate across campaign phases, while recurring motifs help separate visual
continuity from repeated content. Callers can use `scene_for_phase()` to retrieve the
cinematic direction associated with a specific campaign phase.

## Boundaries

The service plans treatments and storyboards; it does not generate images, video, audio,
or provider-specific prompts. PR #24 will translate these typed scenes and shots into a
provider-neutral video prompt model. Rendering or generation adapters can then map that
model to tools such as Veo, Runway, or Kling while preserving human review.
