import pytest

from story import (
    Character,
    CreativeWork,
    Relationship,
    StoryArc,
    StoryBeat,
    Theme,
    Universe,
    WorkKind,
)


def test_builds_universe_with_cross_work_relationships() -> None:
    hope = Theme(id="hope", name="Hope")
    kelvin = Character(id="kelvin", name="Kelvin")
    song = CreativeWork(
        id="no-way-back",
        name="No Way Back",
        kind=WorkKind.SONG,
        theme_ids=("hope",),
        character_ids=("kelvin",),
    )
    book = CreativeWork(
        id="between-hope-and-drowning",
        name="Between Hope and Drowning",
        kind=WorkKind.BOOK,
        theme_ids=("hope",),
        character_ids=("kelvin",),
    )

    universe = Universe(
        id="kelvin-rankie-universe",
        name="Kelvin Rankie Universe",
        works=(song, book),
        characters=(kelvin,),
        themes=(hope,),
        relationships=(
            Relationship(
                source_id="no-way-back",
                target_id="between-hope-and-drowning",
                kind="shares-migration-story",
            ),
        ),
    )

    assert universe.works == (song, book)
    assert universe.relationships[0].kind == "shares-migration-story"


def test_story_arc_preserves_narrative_order() -> None:
    arc = StoryArc(
        id="migration",
        name="Migration",
        beats=(
            StoryBeat(id="departure", summary="Kelvin leaves home."),
            StoryBeat(id="struggle", summary="The journey tests his resolve."),
            StoryBeat(id="resilience", summary="He chooses to continue."),
        ),
    )

    assert tuple(beat.id for beat in arc.beats) == (
        "departure",
        "struggle",
        "resilience",
    )


def test_rejects_duplicate_entity_ids() -> None:
    with pytest.raises(ValueError, match="entity ids must be unique"):
        Universe(
            id="test-universe",
            name="Test Universe",
            themes=(
                Theme(id="hope", name="Hope"),
                Theme(id="hope", name="Hope Again"),
            ),
        )


def test_rejects_relationship_to_unknown_entity() -> None:
    with pytest.raises(ValueError, match="relationship target does not exist"):
        Universe(
            id="test-universe",
            name="Test Universe",
            themes=(Theme(id="hope", name="Hope"),),
            relationships=(
                Relationship(
                    source_id="hope",
                    target_id="missing-theme",
                    kind="contrasts",
                ),
            ),
        )


def test_rejects_empty_entity_identity() -> None:
    with pytest.raises(ValueError, match="id must not be empty"):
        Theme(id=" ", name="Hope")


def test_rejects_duplicate_story_beat_ids() -> None:
    with pytest.raises(ValueError, match="story arc beat ids must be unique"):
        StoryArc(
            id="journey",
            name="Journey",
            beats=(
                StoryBeat(id="departure", summary="Leave."),
                StoryBeat(id="departure", summary="Leave again."),
            ),
        )
