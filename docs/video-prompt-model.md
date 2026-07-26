# Video Prompt Model

The Video Prompt Model converts a cinematic treatment into a typed, provider-agnostic
prompt package. Each cinematic shot becomes a prompt containing its setting, subjects,
action, framing, camera movement, mood, motifs, duration, and continuity guidance.

## Building prompts

```python
from services.video_prompt import VideoPromptService

video_prompt = VideoPromptService().build(treatment, seconds_per_shot=5)
print(video_prompt.render())
```

The output is deterministic and human-reviewable. Use `scene_for_phase()` to select the
prompt package for a particular campaign phase. Scene and total durations are derived
from the configured duration per shot.

## Provider adapters

The domain model contains creative intent, not provider syntax. Future adapters may map
the same `VideoPrompt` to Veo, Runway, Kling, or another video system without changing
the Cinematic Planner or story intelligence.

An adapter is responsible for provider-specific fields such as model names, supported
aspect ratios, seed controls, safety settings, and request payloads. It must preserve the
prompt's narrative purpose and continuity guidance.

## Boundaries

The service does not call AI providers, generate media, publish assets, or select a
provider. Every prompt remains available for human review before any downstream
generation step.
