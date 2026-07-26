"""Load and resolve a provider-agnostic Creative Universe from YAML."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from core.project import Project
from story.models import (
    Character,
    CreativeWork,
    Location,
    Relationship,
    StoryArc,
    StoryBeat,
    Symbol,
    Theme,
    Universe,
    UniverseEntity,
    WorkKind,
)

DEFAULT_UNIVERSE_FILENAME = "universe.yaml"


class UniverseLoadError(ValueError):
    """Raised when a Creative Universe file cannot be loaded or validated."""


class UniverseService:
    """Load a workspace universe and resolve its stable entity references."""

    def __init__(self, project: Project, path: Path | None = None) -> None:
        self.project = project
        self.path = path or project.root / DEFAULT_UNIVERSE_FILENAME

    def load(self) -> Universe:
        """Load and validate the configured Creative Universe YAML file."""
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Creative Universe not found: {self.path}") from exc
        except OSError as exc:
            raise UniverseLoadError(f"Unable to read Creative Universe: {exc}") from exc
        except yaml.YAMLError as exc:
            raise UniverseLoadError(f"Invalid Creative Universe YAML: {exc}") from exc

        if not isinstance(raw, Mapping):
            raise UniverseLoadError("Creative Universe must be a YAML mapping.")

        try:
            universe = self._build_universe(raw)
            self._validate_work_references(universe)
        except (TypeError, ValueError) as exc:
            raise UniverseLoadError(f"Invalid Creative Universe: {exc}") from exc

        return universe

    @staticmethod
    def resolve(universe: Universe, entity_id: str) -> UniverseEntity:
        """Resolve one stable ID to its universe entity."""
        for entity in UniverseService._entities(universe):
            if entity.id == entity_id:
                return entity
        raise KeyError(f"Universe entity not found: {entity_id}")

    @staticmethod
    def _build_universe(data: Mapping[str, Any]) -> Universe:
        return Universe(
            id=UniverseService._required_text(data, "id", "universe"),
            name=UniverseService._required_text(data, "name", "universe"),
            works=tuple(
                UniverseService._build_work(item)
                for item in UniverseService._records(data, "works")
            ),
            characters=tuple(
                UniverseService._build_character(item)
                for item in UniverseService._records(data, "characters")
            ),
            locations=tuple(
                UniverseService._build_location(item)
                for item in UniverseService._records(data, "locations")
            ),
            themes=tuple(
                UniverseService._build_theme(item)
                for item in UniverseService._records(data, "themes")
            ),
            symbols=tuple(
                UniverseService._build_symbol(item)
                for item in UniverseService._records(data, "symbols")
            ),
            arcs=tuple(
                UniverseService._build_arc(item)
                for item in UniverseService._records(data, "arcs")
            ),
            relationships=tuple(
                UniverseService._build_relationship(item)
                for item in UniverseService._records(data, "relationships")
            ),
            metadata=UniverseService._metadata(data.get("metadata", {})),
        )

    @staticmethod
    def _build_work(data: Mapping[str, Any]) -> CreativeWork:
        kind_value = str(data.get("kind", WorkKind.OTHER.value))
        try:
            kind = WorkKind(kind_value)
        except ValueError as exc:
            supported = ", ".join(kind.value for kind in WorkKind)
            raise ValueError(f"unsupported work kind '{kind_value}'; expected one of: {supported}") from exc

        return CreativeWork(
            id=UniverseService._required_text(data, "id", "work"),
            name=UniverseService._required_text(data, "name", "work"),
            description=str(data.get("description", "")),
            kind=kind,
            theme_ids=UniverseService._references(data, "theme_ids", "work"),
            character_ids=UniverseService._references(data, "character_ids", "work"),
            location_ids=UniverseService._references(data, "location_ids", "work"),
            symbol_ids=UniverseService._references(data, "symbol_ids", "work"),
        )

    @staticmethod
    def _build_character(data: Mapping[str, Any]) -> Character:
        return Character(
            id=UniverseService._required_text(data, "id", "character"),
            name=UniverseService._required_text(data, "name", "character"),
            description=str(data.get("description", "")),
            aliases=UniverseService._references(data, "aliases", "character"),
        )

    @staticmethod
    def _build_location(data: Mapping[str, Any]) -> Location:
        return Location(
            id=UniverseService._required_text(data, "id", "location"),
            name=UniverseService._required_text(data, "name", "location"),
            description=str(data.get("description", "")),
            region=str(data.get("region", "")),
        )

    @staticmethod
    def _build_theme(data: Mapping[str, Any]) -> Theme:
        return Theme(
            id=UniverseService._required_text(data, "id", "theme"),
            name=UniverseService._required_text(data, "name", "theme"),
            description=str(data.get("description", "")),
        )

    @staticmethod
    def _build_symbol(data: Mapping[str, Any]) -> Symbol:
        return Symbol(
            id=UniverseService._required_text(data, "id", "symbol"),
            name=UniverseService._required_text(data, "name", "symbol"),
            description=str(data.get("description", "")),
        )

    @staticmethod
    def _build_arc(data: Mapping[str, Any]) -> StoryArc:
        return StoryArc(
            id=UniverseService._required_text(data, "id", "story arc"),
            name=UniverseService._required_text(data, "name", "story arc"),
            description=str(data.get("description", "")),
            beats=tuple(
                StoryBeat(
                    id=UniverseService._required_text(beat, "id", "story beat"),
                    summary=UniverseService._required_text(beat, "summary", "story beat"),
                )
                for beat in UniverseService._records(data, "beats")
            ),
        )

    @staticmethod
    def _build_relationship(data: Mapping[str, Any]) -> Relationship:
        return Relationship(
            source_id=UniverseService._required_text(data, "source_id", "relationship"),
            target_id=UniverseService._required_text(data, "target_id", "relationship"),
            kind=UniverseService._required_text(data, "kind", "relationship"),
            description=str(data.get("description", "")),
        )

    @staticmethod
    def _records(data: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
        raw_items = data.get(key, [])
        if raw_items is None:
            return ()
        if not isinstance(raw_items, list):
            raise TypeError(f"{key} must be a list")

        records: list[Mapping[str, Any]] = []
        for index, item in enumerate(raw_items):
            if not isinstance(item, Mapping):
                raise TypeError(f"{key}[{index}] must be a mapping")
            records.append(item)
        return tuple(records)

    @staticmethod
    def _required_text(data: Mapping[str, Any], key: str, context: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{context} {key} must not be empty")
        return value

    @staticmethod
    def _references(data: Mapping[str, Any], key: str, context: str) -> tuple[str, ...]:
        values = data.get(key, [])
        if values is None:
            return ()
        if not isinstance(values, list) or not all(
            isinstance(value, str) and value.strip() for value in values
        ):
            raise TypeError(f"{context} {key} must be a list of non-empty strings")
        return tuple(values)

    @staticmethod
    def _metadata(value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError("metadata must be a mapping")
        return {str(key): str(item) for key, item in value.items()}

    @staticmethod
    def _entities(universe: Universe) -> tuple[UniverseEntity, ...]:
        return (
            *universe.works,
            *universe.characters,
            *universe.locations,
            *universe.themes,
            *universe.symbols,
            *universe.arcs,
        )

    @staticmethod
    def _validate_work_references(universe: Universe) -> None:
        reference_groups = (
            ("theme", universe.themes, "theme_ids"),
            ("character", universe.characters, "character_ids"),
            ("location", universe.locations, "location_ids"),
            ("symbol", universe.symbols, "symbol_ids"),
        )

        for label, entities, attribute in reference_groups:
            known_ids = {entity.id for entity in entities}
            for work in universe.works:
                for entity_id in getattr(work, attribute):
                    if entity_id not in known_ids:
                        raise ValueError(
                            f"work '{work.id}' references unknown {label}: {entity_id}"
                        )
