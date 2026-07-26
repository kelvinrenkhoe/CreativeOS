from types import SimpleNamespace

import pytest

from story import (
    Character,
    CreativeWork,
    Location,
    Relationship,
    StoryArc,
    StoryBeat,
    StoryContextService,
    Symbol,
    Theme,
    Universe,
    UniverseService,
    WorkKind,
)


def build_universe() -> Universe:
    return Universe(
        id="kelvin-rankie-universe",
        name="Kelvin Rankie Universe",
        works=(
            CreativeWork(
                id="no-lose-guard",
                name="No Lose Guard",
                kind=WorkKind.SONG,
                theme_ids=("resilience",),
                character_ids=("kelvin",),
                location_ids=("london",),
                symbol_ids=("crown",),
            ),
        ),
        themes=(Theme(id="resilience", name="Resilience", description="Protect the vision."),),
        characters=(Character(id="kelvin", name="Kelvin Rankie"),),
        locations=(Location(id="london", name="London", region="England"),),
        symbols=(Symbol(id="crown", name="Crown"),),
        arcs=(
            StoryArc(
                id="still-rising",
                name="Still Rising",
                beats=(StoryBeat(id="resolve", summary="He protects his vision."),),
            ),
            StoryArc(id="unrelated-arc", name="Unrelated"),
        ),
        relationships=(
            Relationship(
                source_id="no-lose-guard",
                target_id="still-rising",
                kind="follows-arc",
            ),
            Relationship(
                source_id="resilience",
                target_id="kelvin",
                kind="embodied-by",
            ),
        ),
    )


class StubUniverseService:
    def __init__(self, universe: Universe) -> None:
        self.universe = universe

    def load(self) -> Universe:
        return self.universe

    @staticmethod
    def resolve(universe: Universe, entity_id: str):
        return UniverseService.resolve(universe, entity_id)


class StubKnowledgeService:
    def build_context(self, song_slug: str | None = None) -> str:
        return f"# Artist Knowledge\n\nContext for {song_slug}"


def build_service(universe: Universe | None = None) -> StoryContextService:
    return StoryContextService(
        SimpleNamespace(),
        universe_service=StubUniverseService(universe or build_universe()),
        knowledge=StubKnowledgeService(),
    )


def test_builds_resolved_knowledge_enriched_context() -> None:
    context = build_service().build("no-lose-guard")

    assert context.universe_id == "kelvin-rankie-universe"
    assert context.work.name == "No Lose Guard"
    assert tuple(theme.id for theme in context.themes) == ("resilience",)
    assert tuple(character.id for character in context.characters) == ("kelvin",)
    assert tuple(location.id for location in context.locations) == ("london",)
    assert tuple(symbol.id for symbol in context.symbols) == ("crown",)
    assert tuple(arc.id for arc in context.arcs) == ("still-rising",)
    assert len(context.relationships) == 2
    assert "Context for no-lose-guard" in context.knowledge


def test_render_returns_deterministic_markdown() -> None:
    rendered = build_service().build("no-lose-guard").render()

    assert rendered.startswith("# Story Context: No Lose Guard")
    assert "## Themes\n\n- **Resilience**: Protect the vision." in rendered
    assert "## Story Arcs\n\n- **Still Rising**" in rendered
    assert "  - He protects his vision." in rendered
    assert "no-lose-guard --follows-arc--> still-rising" in rendered
    assert "## Knowledge\n\n# Artist Knowledge" in rendered


def test_rejects_non_work_entity() -> None:
    with pytest.raises(TypeError, match="requires a creative work: resilience"):
        build_service().build("resilience")


def test_reports_unknown_work() -> None:
    with pytest.raises(KeyError, match="Universe entity not found: missing"):
        build_service().build("missing")
