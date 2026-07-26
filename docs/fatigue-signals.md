# Content and Visual Fatigue Signals

CreativeOS detects explainable signs that a campaign may need creative rotation by
combining existing measurement and asset-intelligence results.

`FatigueSignalService` accepts:

- a current and baseline `CampaignMeasurement`
- optional `CreativeFatigueInput` values for content and visual assets
- configurable moderate and high performance-decline thresholds

It returns deterministic `FatigueSignal` values for:

- platform metrics that decline beyond the configured threshold
- content patterns already marked repetitive by Asset Intelligence
- visual patterns already marked repetitive by Asset Intelligence

Visual concepts can be assessed by rendering their identity, setting, wardrobe,
composition, motifs, and typography direction into stable descriptive text before
passing that text to `AssetIntelligenceService`. This keeps similarity detection
provider-neutral and uses the same mechanism for images, posters, thumbnails, and
cinematic stills.

The service does not fetch analytics, inspect image pixels, call an AI provider,
change a campaign plan, generate replacement assets, or publish anything. A signal
is evidence for human review, not an automatic decision. The recommendation feedback
loop remains a separate roadmap capability.
