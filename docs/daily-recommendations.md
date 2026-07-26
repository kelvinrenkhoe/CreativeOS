# Daily Recommendations

Daily Recommendations turn a coordinated `CampaignPlan` into one clear, reviewable
direction for the current campaign week. The recommendation carries the active narrative
focus, campaign objective, audience, tone, and target platforms without generating or
publishing an asset.

## Command

```bash
creativeos next no-way-back \
  --week 3 \
  --weeks 6 \
  --objective "Grow discovery and meaningful streams" \
  --audience "Afrobeats listeners who value migration stories" \
  --tone "Cinematic, honest, and hopeful" \
  --platform instagram \
  --platform tiktok \
  --platform youtube
```

Use `--arc ARC_ID` when the selected work has more than one story arc.

The command loads the work's Story Context, builds its Narrative Timeline and Campaign
Plan, then selects the direction active during `--week`. Campaign inputs remain explicit
until CreativeOS gains persistent campaign-state and scheduling support.

## Python API

```python
from services.daily_recommendation import DailyRecommendationService

recommendation = DailyRecommendationService().recommend(plan, week=3)
print(recommendation.render())
```

## Boundaries

This capability recommends what the campaign should communicate now. It does not generate
captions, images, videos, prompts, or publishing schedules. It also does not infer the
current campaign week from a date. Human review remains required before a recommendation
becomes a produced or published asset.
