"""Deterministically propose a safe recovered campaign order."""

from models.campaign_dependency_graph import CampaignDependencyGraph
from models.campaign_recovery import (
    CampaignRecoveryError,
    RecoveryAction,
    RecoveryPlan,
    RecoveryRequest,
)
from models.campaign_timeline import CampaignTimeline
from services.campaign_execution import CampaignExecutionState


class CampaignRecoveryService:
    """Recover explicit missed work without mutating campaign state."""

    def recover(
        self,
        timeline: CampaignTimeline,
        dependency_graph: CampaignDependencyGraph,
        execution_state: CampaignExecutionState,
        request: RecoveryRequest,
    ) -> RecoveryPlan:
        """Return a deterministic in-memory recovery proposal."""
        original = tuple(item.item_id for week in timeline.weeks for item in week.items)
        self._validate_inputs(original, timeline, dependency_graph, execution_state, request)

        if not request.missed_item_ids:
            return RecoveryPlan(
                campaign_id=timeline.campaign_id,
                original_item_ids=original,
                recovered_item_ids=original,
                completed_item_ids=execution_state.completed_item_ids,
                fixed_milestone_ids=request.fixed_milestone_ids,
                actions=(),
            )

        completed = set(execution_state.completed_item_ids)
        fixed = set(request.fixed_milestone_ids)
        missed = set(request.missed_item_ids)
        initially_ready = set(execution_state.ready_item_ids)
        original_position = {item_id: index for index, item_id in enumerate(original)}
        recovered: list[str] = []
        placed = set(completed)
        remaining = set(original).difference(completed)

        for slot, original_item_id in enumerate(original):
            if original_item_id in completed:
                recovered.append(original_item_id)
                continue

            if original_item_id in fixed:
                candidate = original_item_id
                if not self._is_ready(candidate, dependency_graph, placed):
                    raise CampaignRecoveryError(
                        f"fixed milestone cannot remain in position: {candidate}"
                    )
            else:
                candidates = tuple(
                    item_id
                    for item_id in remaining
                    if item_id not in fixed
                    and self._is_ready(item_id, dependency_graph, placed)
                    and (item_id not in missed or slot > original_position[item_id] or not fixed)
                )
                if not candidates:
                    if fixed:
                        raise CampaignRecoveryError(
                            "fixed milestone cannot remain after rescheduling missed content"
                        )
                    raise CampaignRecoveryError(
                        f"campaign recovery has no safe item for position {slot + 1}"
                    )
                candidate = min(
                    candidates,
                    key=lambda item_id: (
                        item_id not in initially_ready,
                        item_id in missed,
                        original_position[item_id],
                        item_id,
                    ),
                )

            recovered.append(candidate)
            remaining.remove(candidate)
            placed.add(candidate)

        if remaining:
            raise CampaignRecoveryError("campaign recovery left unscheduled content items")

        recovered_tuple = tuple(recovered)
        self._validate_recovered_order(recovered_tuple, dependency_graph)
        actions = tuple(
            RecoveryAction(
                item_id=item_id,
                original_position=original_position[item_id] + 1,
                recovered_position=recovered_tuple.index(item_id) + 1,
                reason=request.reason,
            )
            for item_id in request.missed_item_ids
            if original_position[item_id] != recovered_tuple.index(item_id)
        )

        return RecoveryPlan(
            campaign_id=timeline.campaign_id,
            original_item_ids=original,
            recovered_item_ids=recovered_tuple,
            completed_item_ids=execution_state.completed_item_ids,
            fixed_milestone_ids=request.fixed_milestone_ids,
            actions=actions,
        )

    @staticmethod
    def _is_ready(
        item_id: str,
        dependency_graph: CampaignDependencyGraph,
        placed: set[str],
    ) -> bool:
        return set(dependency_graph.prerequisites_for(item_id)).issubset(placed)

    @staticmethod
    def _validate_recovered_order(
        recovered: tuple[str, ...],
        dependency_graph: CampaignDependencyGraph,
    ) -> None:
        positions = {item_id: index for index, item_id in enumerate(recovered)}
        for dependency in dependency_graph.dependencies:
            if positions[dependency.prerequisite_id] >= positions[dependency.dependent_id]:
                raise CampaignRecoveryError(
                    "recovered campaign order violates dependency requirements"
                )

    @staticmethod
    def _validate_inputs(
        original: tuple[str, ...],
        timeline: CampaignTimeline,
        dependency_graph: CampaignDependencyGraph,
        execution_state: CampaignExecutionState,
        request: RecoveryRequest,
    ) -> None:
        if timeline.campaign_id != execution_state.campaign_id:
            raise CampaignRecoveryError("execution state belongs to another campaign")
        if original != execution_state.ordered_item_ids:
            raise CampaignRecoveryError("execution state does not match campaign timeline")
        if set(original) != set(dependency_graph.item_ids):
            raise CampaignRecoveryError("dependency graph does not match campaign timeline")

        known = set(original)
        completed = set(execution_state.completed_item_ids)
        for item_id in (*request.missed_item_ids, *request.fixed_milestone_ids):
            if item_id not in known:
                raise CampaignRecoveryError(f"unknown campaign content item: {item_id}")
        for item_id in request.missed_item_ids:
            if item_id in completed:
                raise CampaignRecoveryError(f"completed content cannot be missed: {item_id}")
