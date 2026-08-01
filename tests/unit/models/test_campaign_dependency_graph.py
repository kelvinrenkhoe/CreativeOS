"""Tests for validated campaign content dependency graphs."""

import pytest

from models import (
    CampaignDependency,
    CampaignDependencyGraph,
    CampaignDependencyGraphError,
)


def graph() -> CampaignDependencyGraph:
    return CampaignDependencyGraph(
        item_ids=("announcement", "behind-scenes", "lyric-video", "fan-challenge"),
        dependencies=(
            CampaignDependency("announcement", "behind-scenes"),
            CampaignDependency("announcement", "lyric-video"),
            CampaignDependency("behind-scenes", "fan-challenge"),
            CampaignDependency("lyric-video", "fan-challenge"),
        ),
    )


def test_graph_normalizes_and_orders_items_deterministically() -> None:
    dependency_graph = CampaignDependencyGraph(
        item_ids=("c", "a", "b"),
        dependencies=(
            CampaignDependency("b", "c"),
            CampaignDependency("a", "c"),
        ),
    )

    assert dependency_graph.item_ids == ("a", "b", "c")
    assert dependency_graph.topological_order() == ("a", "b", "c")


def test_graph_exposes_direct_prerequisites_and_dependents() -> None:
    dependency_graph = graph()

    assert dependency_graph.prerequisites_for("fan-challenge") == (
        "behind-scenes",
        "lyric-video",
    )
    assert dependency_graph.dependents_for("announcement") == (
        "behind-scenes",
        "lyric-video",
    )


def test_graph_rejects_unknown_relationship_nodes() -> None:
    with pytest.raises(CampaignDependencyGraphError, match="unknown prerequisite"):
        CampaignDependencyGraph(
            item_ids=("announcement",),
            dependencies=(CampaignDependency("missing", "announcement"),),
        )

    with pytest.raises(CampaignDependencyGraphError, match="unknown dependent"):
        CampaignDependencyGraph(
            item_ids=("announcement",),
            dependencies=(CampaignDependency("announcement", "missing"),),
        )


def test_graph_rejects_duplicate_nodes_and_relationships() -> None:
    with pytest.raises(CampaignDependencyGraphError, match="IDs must be unique"):
        CampaignDependencyGraph(item_ids=("announcement", "announcement"))

    dependency = CampaignDependency("announcement", "lyric-video")
    with pytest.raises(CampaignDependencyGraphError, match="dependencies must be unique"):
        CampaignDependencyGraph(
            item_ids=("announcement", "lyric-video"),
            dependencies=(dependency, dependency),
        )


def test_dependency_rejects_self_reference() -> None:
    with pytest.raises(CampaignDependencyGraphError, match="cannot depend on itself"):
        CampaignDependency("announcement", "announcement")


def test_graph_rejects_cycles() -> None:
    with pytest.raises(CampaignDependencyGraphError, match="contains a cycle"):
        CampaignDependencyGraph(
            item_ids=("announcement", "lyric-video"),
            dependencies=(
                CampaignDependency("announcement", "lyric-video"),
                CampaignDependency("lyric-video", "announcement"),
            ),
        )


def test_evaluate_reports_ready_and_blocked_items() -> None:
    evaluation = graph().evaluate(("announcement",))

    assert evaluation.completed_item_ids == ("announcement",)
    assert evaluation.ready_item_ids == ("behind-scenes", "lyric-video")
    assert tuple(item.item_id for item in evaluation.blocked_items) == ("fan-challenge",)
    assert evaluation.blocked_items[0].unmet_prerequisite_ids == (
        "behind-scenes",
        "lyric-video",
    )


def test_evaluate_unlocks_dependents_after_prerequisites_complete() -> None:
    evaluation = graph().evaluate(
        ("announcement", "behind-scenes", "lyric-video")
    )

    assert evaluation.ready_item_ids == ("fan-challenge",)
    assert evaluation.blocked_items == ()


def test_evaluate_rejects_unknown_or_duplicate_completed_items() -> None:
    dependency_graph = graph()

    with pytest.raises(CampaignDependencyGraphError, match="must be unique"):
        dependency_graph.evaluate(("announcement", "announcement"))

    with pytest.raises(CampaignDependencyGraphError, match="unknown completed"):
        dependency_graph.evaluate(("missing",))


def test_lookup_rejects_unknown_item() -> None:
    with pytest.raises(CampaignDependencyGraphError, match="unknown content item"):
        graph().prerequisites_for("missing")
