from types import SimpleNamespace

import pytest
from story import UniverseLoadError, UniverseService, WorkKind


VALID_UNIVERSE = """
id: kelvin-rankie-universe
name: Kelvin Rankie Universe
metadata:
  artist: Kelvin Rankie
themes:
  - id: resilience
    name: Resilience
characters:
  - id: kelvin
    name: Kelvin
    aliases:
      - Kelvin Rankie
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
"""


def build_service(tmp_path):
    project = SimpleNamespace(root=tmp_path)
    return UniverseService(project)


def test_loads_and_resolves_universe_yaml(tmp_path) -> None:
    (tmp_path / "universe.yaml").write_text(VALID_UNIVERSE, encoding="utf-8")

    service = build_service(tmp_path)
    universe = service.load()

    assert universe.id == "kelvin-rankie-universe"
    assert universe.works[0].kind is WorkKind.SONG
    assert universe.works[0].theme_ids == ("resilience",)
    assert universe.arcs[0].beats[1].id == "resolve"
    assert universe.metadata == {"artist": "Kelvin Rankie"}
    assert service.resolve(universe, "crown").name == "Crown"


def test_reports_missing_universe_file(tmp_path) -> None:
    service = build_service(tmp_path)

    with pytest.raises(FileNotFoundError, match="Creative Universe not found"):
        service.load()


def test_rejects_non_mapping_document(tmp_path) -> None:
    (tmp_path / "universe.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(UniverseLoadError, match="must be a YAML mapping"):
        build_service(tmp_path).load()


def test_rejects_unknown_work_reference(tmp_path) -> None:
    content = VALID_UNIVERSE.replace("      - resilience", "      - missing-theme", 1)
    (tmp_path / "universe.yaml").write_text(content, encoding="utf-8")

    with pytest.raises(
        UniverseLoadError,
        match="work 'no-lose-guard' references unknown theme: missing-theme",
    ):
        build_service(tmp_path).load()


def test_rejects_unknown_relationship_reference(tmp_path) -> None:
    content = VALID_UNIVERSE.replace("target_id: still-rising", "target_id: missing-arc")
    (tmp_path / "universe.yaml").write_text(content, encoding="utf-8")

    with pytest.raises(UniverseLoadError, match="relationship target does not exist"):
        build_service(tmp_path).load()


def test_resolve_rejects_unknown_entity(tmp_path) -> None:
    (tmp_path / "universe.yaml").write_text(VALID_UNIVERSE, encoding="utf-8")
    universe = build_service(tmp_path).load()

    with pytest.raises(KeyError, match="Universe entity not found: missing"):
        UniverseService.resolve(universe, "missing")
