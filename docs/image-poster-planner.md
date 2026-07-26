# Image and Poster Planner

The Image and Poster Planner converts a resolved Story Context and objective-driven
Campaign Plan into provider-neutral visual concepts. Each campaign phase receives one
concept with explicit identity, wardrobe, setting, motifs, mood, exclusions, and format
variants.

## Building an image plan

```python
from services.image_planner import ImagePlannerService

image_plan = ImagePlannerService().build(context, campaign)
print(image_plan.render())
```

Use `concept_for_phase()` to retrieve the visual direction associated with a campaign
phase. Each concept provides reusable variants for cover art, posters, social graphics,
thumbnails, and cinematic stills. Use `concept.format()` to select one variant.

## Visual continuity

Identity and wardrobe requirements are first-class fields. Downstream adapters must
preserve approved subject appearance, phase-specific clothing, recurring settings, and
story motifs across every crop or format. Exclusions identify common unwanted results,
including identity drift, duplicate subjects, distorted hands, unreadable text,
watermarks, and unrequested logos.

Typography policy is format-specific. Promotional formats allow controlled title or
campaign copy, while cinematic stills explicitly prohibit text.

## Provider adapters

The plan contains creative direction, not provider syntax. Future adapters may translate
the same `ImagePlan` into requests for OpenAI Images, Midjourney, Flux, or another image
system without changing story intelligence or campaign planning.

## Boundaries

The service does not generate images, choose a provider, edit reference photos, publish
assets, or bypass human review. Identity reference files and provider-specific controls
remain responsibilities of later generation adapters.
