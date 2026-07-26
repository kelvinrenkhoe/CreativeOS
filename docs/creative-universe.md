# Creative Universe YAML

CreativeOS stores a workspace's connected body of work in a root-level
`universe.yaml` file. Stable IDs connect songs, books, characters, locations,
themes, symbols, story arcs, and relationships without depending on an AI
provider.

## Example

```yaml
id: kelvin-rankie-universe
name: Kelvin Rankie Universe

metadata:
  artist: Kelvin Rankie

themes:
  - id: resilience
    name: Resilience

characters:
  - id: kelvin
    name: Kelvin Rankie

locations:
  - id: london
    name: London
    region: England

symbols:
  - id: crown
    name: Crown

works:
  - id: no-lose-guard
    name: No Lose Guard
    kind: song
    theme_ids:
      - resilience
    character_ids:
      - kelvin
    location_ids:
      - london
    symbol_ids:
      - crown

arcs:
  - id: still-rising
    name: Still Rising
    beats:
      - id: pressure
        summary: Pressure tests his focus.
      - id: resolve
        summary: He protects his vision.

relationships:
  - source_id: no-lose-guard
    target_id: still-rising
    kind: follows-arc
```

Supported work kinds are `song`, `book`, `film`, `podcast`, and `other`.
All entity IDs must be unique. Relationship endpoints and each work's theme,
character, location, and symbol IDs must resolve to existing entities of the
correct type.

## Loading the universe

```python
from core.project import Project
from story import UniverseService

project = Project.discover()
service = UniverseService(project)
universe = service.load()

theme = service.resolve(universe, "resilience")
```

Loading fails with a descriptive error when the YAML shape is invalid, a work
kind is unsupported, an ID is duplicated, or a reference cannot be resolved.
The returned `Universe` remains provider-agnostic so later story-context,
timeline, campaign, and cinematic services can all consume the same source of
truth.
