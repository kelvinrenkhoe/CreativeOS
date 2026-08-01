"""Deterministically evaluate the next actionable campaign content item."""

from dataclasses import dataclass

from models.campaign_dependency_graph import CampaignDependencyGraph
from models.campaign_timeline import CampaignTimeline


class CampaignExecutionError(ValueError):
    """Reject inconsistent or ambiguous campaign execution input."""


@dataclass(frozen=True, slots=True)
class ExecutionBlockedItem:
    """A timeline item and the prerequisites preventing execution."""

    item_id: str
    unmet_prerequisite_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CampaignExecutionState:
    """A read-only deterministic snapshot of campaign execution readiness."""

    campaign_id: str
    ordered_item_ids: tuple[str, ...]
    completed_item_ids: tuple[str, ...]
    ready_item_ids: tuple[str, ...]
    blocked_items: tuple[ExecutionBlockedItem, ...]
    next_item_id: str | None
    next_reason: str | None

    @property
    def remaining_item_ids(self) -> tuple[str, ...]:
        """Return all incomplete items in timeline order."""
        completed = set(self.completed_item_ids)
        return tuple(item_id for item_id in self.ordered_item_ids if item_id not in completed)

    @property
    def is_complete(self) -> bool:
        """Return whether every timeline item is explicitly completed."""
        return not self.remaining_item_ids


class CampaignExecutionService:
    """Combine timeline order and dependency readiness without side effects."""

    def evaluate(
        self,
        timeline: CampaignTimeline,
        dependency_graph: CampaignDependencyGraph,
        completed_item_ids=(),
    ) -> CampaignExecutionState:
        """Build a deterministic execution snapshot from explicit completion state."""
        ordered_item_ids = tuple(
            item.item_id for week in timeline.weeks for item in week.items
        )
        if len(ordered_item_ids) != len(set(ordered_item_ids)):
            raise CampaignExecutionError("timeline content item IDs must be unique")

        timeline_ids = set(ordered_item_ids)
        graph_ids = set(dependency_graph.item_ids)
        if timeline_ids != graph_ids:
            missing_from_graph = tuple(sorted(timeline_ids.difference(graph_ids)))
            if missing_from_graph:
                raise CampaignExecutionError(
                    f"timeline content item missing from dependency graph: {missing_from_graph[0]}"
                )
            missing_from_timeline = tuple(sorted(graph_ids.difference(timeline_ids)))
            raise CampaignExecutionError(
                f"dependency graph content item missing from timeline: {missing_from_timeline[0]}"
            )

        evaluation = dependency_graph.evaluate(completed_item_ids)
        completed = set(evaluation.completed_item_ids)
        ready = set(evaluation.ready_item_ids)
        blocked_by_id = {
            item.item_id: item.unmet_prerequisite_ids for item in evaluation.blocked_items
        }

        completed_in_order = tuple(
            item_id for item_id in ordered_item_ids if item_id in completed
        )
        ready_in_order = tuple(item_id for item_id in ordered_item_ids if item_id in ready)
        blocked_in_order = tuple(
            ExecutionBlockedItem(item_id, blocked_by_id[item_id])
            for item_id in ordered_item_ids
            if item_id in blocked_by_id
        )

        next_item_id = ready_in_order[0] if ready_in_order else None
        next_reason = (
            "Earliest timeline item with all prerequisites completed."
            if next_item_id is not None
            else None
        )

        return CampaignExecutionState(
            campaign_id=timeline.campaign_id,
            ordered_item_ids=ordered_item_ids,
            completed_item_ids=completed_in_order,
            ready_item_ids=ready_in_order,
            blocked_items=blocked_in_order,
            next_item_id=next_item_id,
            next_reason=next_reason,
        )
