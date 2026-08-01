"""Validated dependency graph models for campaign content."""

from dataclasses import dataclass


class CampaignDependencyGraphError(ValueError):
    """Reject invalid or unsafe campaign dependency graphs."""


@dataclass(frozen=True, slots=True, order=True)
class CampaignDependency:
    """A directed prerequisite relationship between two content items."""

    prerequisite_id: str
    dependent_id: str

    def __post_init__(self) -> None:
        prerequisite_id = self._required(self.prerequisite_id, "prerequisite_id")
        dependent_id = self._required(self.dependent_id, "dependent_id")
        if prerequisite_id == dependent_id:
            raise CampaignDependencyGraphError("content item cannot depend on itself")
        object.__setattr__(self, "prerequisite_id", prerequisite_id)
        object.__setattr__(self, "dependent_id", dependent_id)

    @staticmethod
    def _required(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise CampaignDependencyGraphError(f"{field} must be a non-empty string")
        return value.strip()


@dataclass(frozen=True, slots=True)
class BlockedContentItem:
    """A content item and the prerequisites that still block it."""

    item_id: str
    unmet_prerequisite_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CampaignDependencyEvaluation:
    """Deterministic readiness evaluation for one completion snapshot."""

    ready_item_ids: tuple[str, ...]
    blocked_items: tuple[BlockedContentItem, ...]
    completed_item_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CampaignDependencyGraph:
    """A validated acyclic graph of stable campaign content item IDs."""

    item_ids: tuple[str, ...]
    dependencies: tuple[CampaignDependency, ...] = ()

    def __post_init__(self) -> None:
        normalized_ids = tuple(
            CampaignDependency._required(item_id, "item_id") for item_id in self.item_ids
        )
        if len(normalized_ids) != len(set(normalized_ids)):
            raise CampaignDependencyGraphError("content item IDs must be unique")

        known_ids = set(normalized_ids)
        normalized_dependencies = tuple(sorted(self.dependencies))
        if len(normalized_dependencies) != len(set(normalized_dependencies)):
            raise CampaignDependencyGraphError("campaign dependencies must be unique")
        for dependency in normalized_dependencies:
            if dependency.prerequisite_id not in known_ids:
                raise CampaignDependencyGraphError(
                    f"unknown prerequisite content item: {dependency.prerequisite_id}"
                )
            if dependency.dependent_id not in known_ids:
                raise CampaignDependencyGraphError(
                    f"unknown dependent content item: {dependency.dependent_id}"
                )

        object.__setattr__(self, "item_ids", tuple(sorted(normalized_ids)))
        object.__setattr__(self, "dependencies", normalized_dependencies)
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        """Return a stable prerequisite-first ordering or reject cycles."""
        prerequisites = {
            item_id: set(self.prerequisites_for(item_id)) for item_id in self.item_ids
        }
        ordered: list[str] = []
        remaining = set(self.item_ids)
        while remaining:
            ready = tuple(
                sorted(item_id for item_id in remaining if not prerequisites[item_id])
            )
            if not ready:
                raise CampaignDependencyGraphError("campaign dependency graph contains a cycle")
            ordered.extend(ready)
            remaining.difference_update(ready)
            for item_id in remaining:
                prerequisites[item_id].difference_update(ready)
        return tuple(ordered)

    def prerequisites_for(self, item_id: str) -> tuple[str, ...]:
        """Return direct prerequisite IDs for one known content item."""
        item_id = self._known(item_id)
        return tuple(
            dependency.prerequisite_id
            for dependency in self.dependencies
            if dependency.dependent_id == item_id
        )

    def dependents_for(self, item_id: str) -> tuple[str, ...]:
        """Return direct dependent IDs for one known content item."""
        item_id = self._known(item_id)
        return tuple(
            dependency.dependent_id
            for dependency in self.dependencies
            if dependency.prerequisite_id == item_id
        )

    def evaluate(self, completed_item_ids=()) -> CampaignDependencyEvaluation:
        """Classify incomplete items as ready or blocked."""
        completed = tuple(
            sorted(
                CampaignDependency._required(item_id, "completed_item_id")
                for item_id in completed_item_ids
            )
        )
        if len(completed) != len(set(completed)):
            raise CampaignDependencyGraphError("completed content item IDs must be unique")
        unknown = tuple(sorted(set(completed).difference(self.item_ids)))
        if unknown:
            raise CampaignDependencyGraphError(
                f"unknown completed content item: {unknown[0]}"
            )

        completed_set = set(completed)
        ready: list[str] = []
        blocked: list[BlockedContentItem] = []
        for item_id in self.topological_order():
            if item_id in completed_set:
                continue
            unmet = tuple(
                prerequisite_id
                for prerequisite_id in self.prerequisites_for(item_id)
                if prerequisite_id not in completed_set
            )
            if unmet:
                blocked.append(BlockedContentItem(item_id, unmet))
            else:
                ready.append(item_id)

        return CampaignDependencyEvaluation(
            ready_item_ids=tuple(ready),
            blocked_items=tuple(blocked),
            completed_item_ids=completed,
        )

    def _known(self, item_id: str) -> str:
        item_id = CampaignDependency._required(item_id, "item_id")
        if item_id not in self.item_ids:
            raise CampaignDependencyGraphError(f"unknown content item: {item_id}")
        return item_id
