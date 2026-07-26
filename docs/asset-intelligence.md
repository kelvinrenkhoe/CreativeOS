# Asset Intelligence

Asset Intelligence gives CreativeOS a deterministic signal for whether a proposed
campaign asset is meaningfully different from work already recorded in campaign
memory.

## Responsibilities

`AssetIntelligenceService`:

- normalizes words without depending on an AI provider;
- compares word shingles using Jaccard similarity;
- returns novelty and similarity scores from `0.0` to `1.0`;
- identifies the closest prior campaign-memory entry;
- flags content at or above a configurable repetition threshold;
- returns a simple `use` or `revise` recommendation.

The service advises downstream planners and human reviewers. It does not generate,
rewrite, reject, or publish an asset.

## Example

```python
from services.asset_intelligence import AssetIntelligenceService
from services.campaign_memory import CampaignMemory

memory = CampaignMemory()
memory.add(
    relative_path="captions/instagram.md",
    purpose="Instagram launch caption",
    content="Follow the journey and stream the new single today.",
)

assessment = AssetIntelligenceService().assess(
    "Follow the journey and stream the new single today.",
    memory,
)

assert assessment.is_repetitive
assert assessment.recommendation == "revise"
```

The deterministic implementation creates a stable baseline. Semantic embeddings or
provider-backed analysis can be added later behind a separate abstraction without
changing the assessment model used by planners.
