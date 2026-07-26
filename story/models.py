"""Provider-agnostic domain models for a creator's connected body of work."""

from dataclasses import dataclass, field
from enum import StrEnum


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class UniverseEntity:
    """Base identity shared by Creative Universe entities."""

    id: str
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        _require_text(self.id, "id")
        _require_text(self.name, "name")


class WorkKind(StrEnum):
    """Supported kinds of authored creative work."""

    SONG = "song"
    BOOK = "book"
    FILM = "film"
    PODCAST = "podcast"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class CreativeWork(UniverseEntity):
    """A song, book, film, podcast, or other authored work."""

    kind: WorkKind = WorkKind.OTHER
    theme_ids: tuple[str, ...] = ()
    character_ids: tuple[str, ...] = ()
    location_ids: tuple[str, ...] = ()
    symbol_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Character(UniverseEntity):
    """A real or fictional identity represented in the universe."""

    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Location(UniverseEntity):
    """A real or fictional place used by creative works."""

    region: str = ""


@dataclass(frozen=True, slots=True)
class Theme(UniverseEntity):
    """A recurring narrative idea or concern."""


@dataclass(frozen=True, slots=True)
class Symbol(UniverseEntity):
    """A recurring visual or narrative motif."""


@dataclass(frozen=True, slots=True)
class StoryBeat:
    """One ordered change in a narrative arc."""

    id: str
    summary: str

    def __post_init__(self) -> None:
        _require_text(self.id, "id")
        _require_text(self.summary, "summary")


@dataclass(frozen=True, slots=True)
class StoryArc(UniverseEntity):
    """An ordered narrative progression reusable across execution formats."""

    beats: tuple[StoryBeat, ...] = ()

    def __post_init__(self) -> None:
        super(StoryArc, self).__post_init__()
        beat_ids = [beat.id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("story arc beat ids must be unique")


@dataclass(frozen=True, slots=True)
class Relationship:
    """A typed directional link between two universe entities."""

    source_id: str
    target_id: str
    kind: str
    description: str = ""

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.target_id, "target_id")
        _require_text(self.kind, "kind")
        if self.source_id == self.target_id:
            raise ValueError("a relationship must connect two different entities")


@dataclass(frozen=True, slots=True)
class Universe:
    """Root aggregate for a creator's connected body of work."""

    id: str
    name: str
    works: tuple[CreativeWork, ...] = ()
    characters: tuple[Character, ...] = ()
    locations: tuple[Location, ...] = ()
    themes: tuple[Theme, ...] = ()
    symbols: tuple[Symbol, ...] = ()
    arcs: tuple[StoryArc, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.id, "id")
        _require_text(self.name, "name")

        entities = (
            *self.works,
            *self.characters,
            *self.locations,
            *self.themes,
            *self.symbols,
            *self.arcs,
        )
        entity_ids = [entity.id for entity in entities]

        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("universe entity ids must be unique")

        known_ids = set(entity_ids)
        for relationship in self.relationships:
            if relationship.source_id not in known_ids:
                raise ValueError(
                    f"relationship source does not exist: {relationship.source_id}"
                )
            if relationship.target_id not in known_ids:
                raise ValueError(
                    f"relationship target does not exist: {relationship.target_id}"
                )
