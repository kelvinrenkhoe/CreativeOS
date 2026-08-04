"""Bounded orchestration over the one-action campaign runner API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from api.campaign_runner import CampaignRunnerAPI, CampaignRunnerResult

POLICY_ONCE = "once"
POLICY_UNTIL_BLOCKED = "until-blocked"
POLICY_UNTIL_COMPLETE = "until-complete"
SUPPORTED_POLICIES = (POLICY_ONCE, POLICY_UNTIL_BLOCKED, POLICY_UNTIL_COMPLETE)
DEFAULT_MAX_STEPS = 100
COMPLETION_ACTIONS = {"campaign-completed", "campaign-finished", "completed"}
COMPLETION_STAGES = {"completed", "finished"}


class CampaignRunner(Protocol):
    """Minimal runner contract required by the orchestrator."""

    def advance(
        self,
        campaign_id: str,
        *,
        now: datetime | None = None,
    ) -> CampaignRunnerResult:
        """Advance at most one durable runtime action."""
        ...


@dataclass(frozen=True, slots=True)
class CampaignOrchestrationEvent:
    """One deterministic orchestration event."""

    kind: str
    step: int
    campaign_id: str
    stage: str | None = None
    action: str | None = None
    request_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class CampaignOrchestrationResult:
    """Structured result from a bounded orchestration run."""

    campaign_id: str
    policy: str
    steps: int = 0
    completed: bool = False
    paused: bool = False
    uncertain: bool = False
    events: tuple[CampaignOrchestrationEvent, ...] = ()
    last_result: CampaignRunnerResult | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def successful(self) -> bool:
        """Return whether orchestration stopped without errors."""
        return not self.errors


class CampaignOrchestratorAPI:
    """Repeat safe one-action advancement until a bounded stop condition."""

    def __init__(self, runner: CampaignRunner) -> None:
        self.runner = runner

    @classmethod
    def for_project(cls, project, **runner_options) -> "CampaignOrchestratorAPI":
        """Build an orchestrator around the standard campaign runner API."""
        return cls(CampaignRunnerAPI(project, **runner_options))

    def run(
        self,
        campaign_id: str,
        *,
        policy: str = POLICY_ONCE,
        max_steps: int = DEFAULT_MAX_STEPS,
        now: datetime | None = None,
    ) -> CampaignOrchestrationResult:
        """Advance according to policy while preserving runner safety boundaries."""
        normalized_policy = self._policy(policy)
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        events = [
            CampaignOrchestrationEvent(
                kind="campaign-started",
                step=0,
                campaign_id=campaign_id,
                detail=normalized_policy,
            )
        ]
        previous_signature = None
        last_result = None

        for step in range(1, max_steps + 1):
            events.append(
                CampaignOrchestrationEvent(
                    kind="step-started",
                    step=step,
                    campaign_id=campaign_id,
                )
            )
            current = self.runner.advance(campaign_id, now=now)
            last_result = current
            events.append(self._result_event(current, step))

            completed = self._completed(current)
            blocked = bool(current.errors or current.paused or current.uncertain)
            signature = (
                current.stage,
                current.action,
                current.request_id,
                current.paused,
                current.uncertain,
                current.errors,
            )
            no_progress = previous_signature == signature

            if completed:
                events.append(
                    CampaignOrchestrationEvent(
                        kind="campaign-finished",
                        step=step,
                        campaign_id=campaign_id,
                        stage=current.stage,
                        action=current.action,
                    )
                )
                return self._result(
                    campaign_id,
                    normalized_policy,
                    step,
                    events,
                    current,
                    completed=True,
                )

            if blocked:
                events.append(
                    CampaignOrchestrationEvent(
                        kind="campaign-blocked",
                        step=step,
                        campaign_id=campaign_id,
                        stage=current.stage,
                        action=current.action,
                        detail=self._blocked_detail(current),
                    )
                )
                return self._result(
                    campaign_id,
                    normalized_policy,
                    step,
                    events,
                    current,
                )

            if normalized_policy == POLICY_ONCE:
                return self._result(
                    campaign_id,
                    normalized_policy,
                    step,
                    events,
                    current,
                )

            if no_progress:
                warning = "orchestration stopped because the runner made no progress"
                events.append(
                    CampaignOrchestrationEvent(
                        kind="campaign-stalled",
                        step=step,
                        campaign_id=campaign_id,
                        stage=current.stage,
                        action=current.action,
                        detail=warning,
                    )
                )
                return self._result(
                    campaign_id,
                    normalized_policy,
                    step,
                    events,
                    current,
                    warnings=(warning,),
                )

            previous_signature = signature

        warning = f"orchestration stopped after max_steps={max_steps}"
        events.append(
            CampaignOrchestrationEvent(
                kind="campaign-step-limit-reached",
                step=max_steps,
                campaign_id=campaign_id,
                detail=warning,
            )
        )
        return self._result(
            campaign_id,
            normalized_policy,
            max_steps,
            events,
            last_result,
            warnings=(warning,),
        )

    @staticmethod
    def _policy(policy: str) -> str:
        normalized = policy.strip().casefold().replace("_", "-")
        if normalized not in SUPPORTED_POLICIES:
            supported = ", ".join(SUPPORTED_POLICIES)
            raise ValueError(f"unsupported orchestration policy: {policy}. Supported: {supported}")
        return normalized

    @staticmethod
    def _completed(result: CampaignRunnerResult) -> bool:
        action = (result.action or "").strip().casefold()
        stage = (result.stage or "").strip().casefold()
        return action in COMPLETION_ACTIONS or stage in COMPLETION_STAGES

    @staticmethod
    def _result_event(
        result: CampaignRunnerResult,
        step: int,
    ) -> CampaignOrchestrationEvent:
        if result.errors:
            kind = "step-failed"
            detail = "; ".join(result.errors)
        elif result.uncertain:
            kind = "step-uncertain"
            detail = "runtime action is uncertain"
        elif result.paused:
            kind = "step-paused"
            detail = "runtime paused"
        else:
            kind = "step-completed"
            detail = None
        return CampaignOrchestrationEvent(
            kind=kind,
            step=step,
            campaign_id=result.campaign_id,
            stage=result.stage,
            action=result.action,
            request_id=result.request_id,
            detail=detail,
        )

    @staticmethod
    def _blocked_detail(result: CampaignRunnerResult) -> str:
        if result.errors:
            return "; ".join(result.errors)
        if result.uncertain:
            return "runtime action is uncertain"
        return "runtime paused"

    @staticmethod
    def _result(
        campaign_id: str,
        policy: str,
        steps: int,
        events: list[CampaignOrchestrationEvent],
        last_result: CampaignRunnerResult | None,
        *,
        completed: bool = False,
        warnings: tuple[str, ...] = (),
    ) -> CampaignOrchestrationResult:
        return CampaignOrchestrationResult(
            campaign_id=campaign_id,
            policy=policy,
            steps=steps,
            completed=completed,
            paused=bool(last_result and last_result.paused),
            uncertain=bool(last_result and last_result.uncertain),
            events=tuple(events),
            last_result=last_result,
            warnings=warnings,
            errors=last_result.errors if last_result else (),
        )
