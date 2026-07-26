# Campaign Orchestration

Campaign orchestration is the first Phase 5 capability. It connects the existing planning and
creative-direction services into one reviewable campaign run and guards its lifecycle.

## Lifecycle

`planned → in-production → ready → published → measured → completed`

A run advances one stage at a time. The following transitions require evidence:

| Target stage | Required evidence |
|---|---|
| `ready` | `approved-assets` |
| `published` | `publication-receipt` |
| `measured` | `campaign-measurement` |

Each evidence record includes a stable reference and the person who recorded it. This preserves
the human-review boundary and provides traceability without embedding provider credentials or
platform-specific behaviour.

## Boundaries

`CampaignOrchestrationService.prepare` composes the existing campaign plan, cinematic planner,
video prompt model, and image planner. It does not generate media, call an AI provider, publish
content, fetch analytics, or apply learned recommendations.

`advance` records lifecycle progress only. Publishing still belongs to `PublishingService`,
measurement still consumes normalized performance data, and strategy changes still require the
recommendation feedback workflow.
