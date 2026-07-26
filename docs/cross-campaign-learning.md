# Cross-Campaign Learning

CreativeOS can identify reusable patterns across completed campaigns while keeping every
future campaign decision under human control.

`CrossCampaignLearningService.learn` consumes completed outcomes containing:

- the original `CampaignPlan` and its human-supplied intent
- the final normalized `CampaignMeasurement`
- the reviewed `FeedbackOutcome`

## Learned evidence

The service produces two provider-neutral pattern types:

1. **Metric benchmarks** group matching objective, audience, tone, platform, and metric
   contexts. The benchmark reports the observed average, supporting campaign IDs, and
   evidence count.
2. **Accepted strategy patterns** identify the same recommendation kind accepted by a
   human across multiple campaigns. Platform and metric details remain part of the
   pattern when relevant.

By default, a pattern needs evidence from at least two distinct campaigns. Callers may
raise that threshold. Different campaign intents are not silently combined, and every
result is deterministically ordered for review and downstream storage.

## Advisory boundary

Cross-campaign learning is descriptive evidence, not an automatic optimization engine.
It does not mutate a `CampaignPlan`, select a future strategy, generate assets, call an
AI provider, fetch live analytics, or publish content. A later planning integration may
present these patterns alongside a new campaign brief, but a human must decide whether
they apply.
