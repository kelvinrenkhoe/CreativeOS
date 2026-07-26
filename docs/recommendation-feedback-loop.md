# Recommendation Feedback Loop

CreativeOS turns deterministic fatigue evidence into explainable strategy proposals while
keeping campaign decisions in human hands.

`RecommendationFeedbackService.recommend` consumes a `FatigueAssessment` and proposes:

- reviewing a platform and metric strategy when performance declines
- rotating a repeated content pattern
- refreshing a repeated visual direction

Each recommendation carries the source signal, priority, action, reason, and relevant
asset or platform details. Recommendation IDs and ordering are deterministic for the
ordered assessment supplied by `FatigueSignalService`.

## Human review

`RecommendationFeedbackService.review` accepts explicit `accept` or `reject`
decisions from a named person. It validates that every decision targets a real
recommendation and returns accepted, rejected, and pending recommendations.

An accepted recommendation is still only a reviewed strategy proposal. This capability
does not mutate a `CampaignPlan`, generate replacement assets, call an AI provider,
publish content, or connect to live analytics. A later orchestration layer may use
accepted recommendations as inputs, but must preserve the existing approval boundaries.
