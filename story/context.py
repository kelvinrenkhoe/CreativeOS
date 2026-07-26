"""Build provider-agnostic, knowledge-enriched story context."""

from dataclasses import dataclass

from core.project import Project
from services.knowledge import KnowledgeService
from story.models import (
    Character,
    CreativeWork,
    Location,
    Relationship,
    StoryArc,
    Symbol,
    Theme,
    Universe,
    UniverseEntity,
)
from story.service import UniverseService


@dataclass(frozen=True, slots=True)
class StoryContext:
    """Resolved narrative context for one creative work."""

    universe_id: str
    universe_name: str
    work: CreativeWork
    themes: tuple[Theme, ...]
    characters: tuple[Character, ...]
    locations: tuple[Location, ...]
    symbols: tuple[Symbol, ...]
    arcs: tuple[StoryArc, ...]
    relationships: tuple[Relationship, ...]
    knowledge: str

    def render(self) -> str:
        """Render a deterministic Markdown context for downstream consumers."""
        sections = [
            f"# Story Context: {self.work.name}",
            self._entity_section("Themes", self.themes),
            self._entity_section("Characters", self.characters),
            self._entity_section("Locations", self.locations),
            self._entity_section("Symbols", self.symbols),
            self._arc_section(),
            self._relationship_section(),
        ]
        if self.knowledge:
            sections.append(f"## Knowledge\n\n{self.knowledge}")
        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def _entity_section(title: str, entities: tuple[UniverseEntity, ...]) -> str:
        if not entities:
            return ""
        lines = [
            f"- **{entity.name}**" + (f": {entity.description}" if entity.description else "")
            for entity in entities
        ]
        return f"## {title}\n\n" + "\n".join(lines)

    def _arc_section(self) -> str:
        if not self.arcs:
            return ""
        lines: list[str] = []
        for arc in self.arcs:
            lines.append(f"- **{arc.name}**")
            lines.extend(f"  - {beat.summary}" for beat in arc.beats)
        return "## Story Arcs\n\n" + "\n".join(lines)

    def _relationship_section(self) -> str:
        if not self.relationships:
            return ""
        lines = [
            f"- {relationship.source_id} --{relationship.kind}--> {relationship.target_id}"
            + (f": {relationship.description}" if relationship.description else "")
            for relationship in self.relationships
        ]
        return "## Relationships\n\n" + "\n".join(lines)


class StoryContextService:
    """Resolve a work's universe references and available knowledge."""

    def __init__(
        self,
        project: Project,
        universe_service: UniverseService | None = None,
        knowledge: KnowledgeService | None = None,
    ) -> None:
        self.universe_service = universe_service or UniverseService(project)
        self.knowledge = knowledge or KnowledgeService(project.knowledge_path)

    def build(self, work_id: str) -> StoryContext:
        """Build context for one creative work identified by its stable ID."""
        universe = self.universe_service.load()
        work = self.universe_service.resolve(universe, work_id)
        if not isinstance(work, CreativeWork):
            raise TypeError(f"Story context requires a creative work: {work_id}")

        arcs = self._connected_arcs(universe, work.id)
        selected_ids = {
            work.id,
            *work.theme_ids,
            *work.character_ids,
            *work.location_ids,
            *work.symbol_ids,
            *(arc.id for arc in arcs),
        }

        return StoryContext(
            universe_id=universe.id,
            universe_name=universe.name,
            work=work,
            themes=self._resolve_many(universe, work.theme_ids, Theme),
            characters=self._resolve_many(universe, work.character_ids, Character),
            locations=self._resolve_many(universe, work.location_ids, Location),
            symbols=self._resolve_many(universe, work.symbol_ids, Symbol),
            arcs=arcs,
            relationships=tuple(
                relationship
                for relationship in universe.relationships
                if relationship.source_id in selected_ids and relationship.target_id in selected_ids
            ),
            knowledge=self.knowledge.build_context(work.id),
        )

    def _resolve_many[EntityT: UniverseEntity](
        self,
        universe: Universe,
        entity_ids: tuple[str, ...],
        expected_type: type[EntityT],
    ) -> tuple[EntityT, ...]:
        entities: list[EntityT] = []
        for entity_id in entity_ids:
            entity = self.universe_service.resolve(universe, entity_id)
            if not isinstance(entity, expected_type):
                raise TypeError(
                    f"Expected {expected_type.__name__} for '{entity_id}', "
                    f"got {type(entity).__name__}"
                )
            entities.append(entity)
        return tuple(entities)

    @staticmethod
    def _connected_arcs(universe: Universe, work_id: str) -> tuple[StoryArc, ...]:
        arc_ids = {arc.id for arc in universe.arcs}
        connected_ids = {
            endpoint
            for relationship in universe.relationships
            if relationship.source_id == work_id or relationship.target_id == work_id
            for endpoint in (relationship.source_id, relationship.target_id)
            if endpoint in arc_ids
        }
        return tuple(arc for arc in universe.arcs if arc.id in connected_ids)
