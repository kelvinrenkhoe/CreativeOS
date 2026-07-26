"""Coordinate campaign capabilities through an approval-gated lifecycle."""

from dataclasses import dataclass, replace

from services.campaign_planner import CampaignPlan
from services.cinematic_planner import CinematicPlannerService, CinematicTreatment
from services.image_planner import ImagePlan, ImagePlannerService
from services.video_prompt import VideoPrompt, VideoPromptService
from story.context import StoryContext


STAGES = (
    "planned",
    "in-production",
    "ready",
    "published",
    "measured",
    "completed",
)


@dataclass(frozen=True, slots=True)
class WorkflowEvidence:
    """A human-reviewable reference that permits one lifecycle transition."""

    kind: str
    reference_id: str
    recorded_by: str


@dataclass(frozen=True, slots=True)
class CampaignRun:
    """One coordinated campaign package and its current lifecycle state."""

    campaign_id: str
    work_id: str
    stage: str
    plan: CampaignPlan
    cinematic_treatment: CinematicTreatment
    video_prompt: VideoPrompt
    image_plan: ImagePlan
    evidence: tuple[WorkflowEvidence, ...] = ()

    @property
    def requires_action(self) -> str:
        """Return the evidence or action required before the next transition."""
        requirements = {
            "planned": "Begin production",
            "in-production": "Record approved-assets evidence",
            "ready": "Record publication-receipt evidence",
            "published": "Record campaign-measurement evidence",
            "measured": "Complete the campaign",
            "completed": "No further action",
        }
        return requirements[self.stage]


class CampaignOrchestrationService:
    """Compose existing plans and guard lifecycle transitions without side effects."""

    _REQUIRED_EVIDENCE = {
        "ready": "approved-assets",
        "published": "publication-receipt",
        "measured": "campaign-measurement",
    }

    def prepare(
        self,
        campaign_id: str,
        context: StoryContext,
        plan: CampaignPlan,
        *,
        seconds_per_shot: int = 5,
    ) -> CampaignRun:
        """Build a coordinated run without generating, publishing, or fetching data."""
        campaign_id = self._required(campaign_id, "campaign_id")
        treatment = CinematicPlannerService().build(context, plan)
        return CampaignRun(
            campaign_id=campaign_id,
            work_id=plan.work_id,
            stage="planned",
            plan=plan,
            cinematic_treatment=treatment,
            video_prompt=VideoPromptService().build(
                treatment,
                seconds_per_shot=seconds_per_shot,
            ),
            image_plan=ImagePlannerService().build(context, plan),
        )

    def advance(
        self,
        run: CampaignRun,
        target_stage: str,
        *,
        evidence: WorkflowEvidence | None = None,
    ) -> CampaignRun:
        """Advance exactly one stage after validating its required evidence."""
        current = self._stage(run.stage)
        target = self._stage(target_stage)
        current_index = STAGES.index(current)
        if current_index == len(STAGES) - 1:
            raise ValueError("completed campaign cannot advance")
        expected = STAGES[current_index + 1]
        if target != expected:
            raise ValueError(f"campaign must advance from {current} to {expected}")

        required_kind = self._REQUIRED_EVIDENCE.get(target)
        if required_kind is None:
            if evidence is not None:
                raise ValueError(f"{target} transition does not accept evidence")
            return replace(run, stage=target)

        validated = self._evidence(evidence, required_kind)
        if any(item.kind == validated.kind for item in run.evidence):
            raise ValueError(f"evidence already recorded: {validated.kind}")
        return replace(run, stage=target, evidence=(*run.evidence, validated))

    @classmethod
    def _evidence(
        cls,
        evidence: WorkflowEvidence | None,
        required_kind: str,
    ) -> WorkflowEvidence:
        if evidence is None:
            raise PermissionError(f"{required_kind} evidence is required")
        kind = cls._required(evidence.kind, "evidence kind").casefold()
        if kind != required_kind:
            raise PermissionError(f"{required_kind} evidence is required")
        return WorkflowEvidence(
            kind=kind,
            reference_id=cls._required(evidence.reference_id, "reference_id"),
            recorded_by=cls._required(evidence.recorded_by, "recorded_by"),
        )

    @classmethod
    def _stage(cls, value: str) -> str:
        stage = cls._required(value, "stage").casefold()
        if stage not in STAGES:
            raise ValueError(f"unsupported campaign stage: {stage}")
        return stage

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
