"""Persist and restore complete campaign orchestration runs."""

import json
from dataclasses import asdict
from json import JSONDecodeError
from pathlib import Path
from typing import Protocol

from services.campaign_orchestration import STAGES, CampaignRun, WorkflowEvidence
from services.campaign_planner import (
    CampaignIntent,
    CampaignPhaseDirection,
    CampaignPlan,
)
from services.cinematic_planner import (
    CinematicScene,
    CinematicTreatment,
    ShotDirection,
)
from services.image_planner import ImageConcept, ImageFormat, ImagePlan
from services.video_prompt import VideoPrompt, VideoScenePrompt, VideoShotPrompt

RUN_STATE_VERSION = "1"


class CampaignRunStateError(Exception):
    """Base exception for campaign run persistence."""


class CampaignRunNotFoundError(CampaignRunStateError):
    """Raised when a saved campaign run does not exist."""


class CampaignRunCorruptedError(CampaignRunStateError):
    """Raised when a saved campaign run cannot be decoded."""


class CampaignRunVersionError(CampaignRunStateError):
    """Raised when a saved campaign run uses an unsupported schema version."""


class CampaignRunValidationError(CampaignRunStateError):
    """Raised when a campaign run snapshot is internally inconsistent."""


class CampaignRunStore(Protocol):
    """Persistence boundary for campaign run snapshots."""

    def save(self, run: CampaignRun) -> None:
        """Persist a complete campaign run."""

    def load(self, campaign_id: str) -> CampaignRun:
        """Restore a complete campaign run."""


class JsonCampaignRunStore:
    """Store versioned campaign run snapshots as deterministic JSON files."""

    _EVIDENCE_BY_STAGE = {
        "ready": "approved-assets",
        "published": "publication-receipt",
        "measured": "campaign-measurement",
    }

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def save(self, run: CampaignRun) -> None:
        """Validate and atomically replace a campaign run snapshot."""
        self._validate(run)
        path = self._path(run.campaign_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"version": RUN_STATE_VERSION, "campaign_run": asdict(run)},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def load(self, campaign_id: str) -> CampaignRun:
        """Load a campaign run without advancing or otherwise mutating it."""
        path = self._path(campaign_id)
        if not path.is_file():
            raise CampaignRunNotFoundError(f"Campaign run not found: {campaign_id}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (JSONDecodeError, UnicodeDecodeError) as error:
            raise CampaignRunCorruptedError(f"Campaign run is corrupt: {campaign_id}") from error

        try:
            root = self._object(payload, "snapshot")
            version = self._string(root["version"], "version")
            if version != RUN_STATE_VERSION:
                raise CampaignRunVersionError(f"Unsupported campaign run version: {version}")
            run = self._run(self._object(root["campaign_run"], "campaign_run"))
        except CampaignRunVersionError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise CampaignRunCorruptedError(
                f"Campaign run has an invalid structure: {campaign_id}"
            ) from error

        if run.campaign_id != campaign_id:
            raise CampaignRunValidationError(
                f"Campaign ID mismatch: expected {campaign_id}, found {run.campaign_id}"
            )
        self._validate(run)
        return run

    def _path(self, campaign_id: str) -> Path:
        normalized = campaign_id.strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
        ):
            raise CampaignRunValidationError("campaign_id must be a safe file name")
        return self.directory / f"{normalized}.json"

    @classmethod
    def _validate(cls, run: CampaignRun) -> None:
        if run.stage not in STAGES:
            raise CampaignRunValidationError(f"Unsupported campaign stage: {run.stage}")
        work_ids = {
            run.work_id,
            run.plan.work_id,
            run.cinematic_treatment.work_id,
            run.video_prompt.work_id,
            run.image_plan.work_id,
        }
        if len(work_ids) != 1:
            raise CampaignRunValidationError("Campaign run work IDs do not match")

        stage_index = STAGES.index(run.stage)
        expected = tuple(
            kind
            for target, kind in cls._EVIDENCE_BY_STAGE.items()
            if STAGES.index(target) <= stage_index
        )
        actual = tuple(item.kind for item in run.evidence)
        if actual != expected:
            raise CampaignRunValidationError(
                f"Campaign evidence does not match stage {run.stage}: {actual}"
            )
        for item in run.evidence:
            if not item.reference_id.strip() or not item.recorded_by.strip():
                raise CampaignRunValidationError("Campaign evidence fields must not be empty")

    @classmethod
    def _run(cls, value: dict[str, object]) -> CampaignRun:
        return CampaignRun(
            campaign_id=cls._string(value["campaign_id"], "campaign_id"),
            work_id=cls._string(value["work_id"], "work_id"),
            stage=cls._string(value["stage"], "stage"),
            plan=cls._plan(cls._object(value["plan"], "plan")),
            cinematic_treatment=cls._treatment(
                cls._object(value["cinematic_treatment"], "cinematic_treatment")
            ),
            video_prompt=cls._video_prompt(cls._object(value["video_prompt"], "video_prompt")),
            image_plan=cls._image_plan(cls._object(value["image_plan"], "image_plan")),
            evidence=tuple(
                WorkflowEvidence(
                    kind=cls._string(item["kind"], "evidence.kind"),
                    reference_id=cls._string(item["reference_id"], "evidence.reference_id"),
                    recorded_by=cls._string(item["recorded_by"], "evidence.recorded_by"),
                )
                for item in cls._objects(value["evidence"], "evidence")
            ),
        )

    @classmethod
    def _plan(cls, value: dict[str, object]) -> CampaignPlan:
        intent = cls._object(value["intent"], "plan.intent")
        return CampaignPlan(
            work_id=cls._string(value["work_id"], "plan.work_id"),
            work_name=cls._string(value["work_name"], "plan.work_name"),
            total_weeks=cls._integer(value["total_weeks"], "plan.total_weeks"),
            intent=CampaignIntent(
                objective=cls._string(intent["objective"], "intent.objective"),
                audience=cls._string(intent["audience"], "intent.audience"),
                tone=cls._string(intent["tone"], "intent.tone"),
                platforms=cls._strings(intent["platforms"], "intent.platforms"),
            ),
            phases=tuple(
                CampaignPhaseDirection(
                    phase_number=cls._integer(item["phase_number"], "phase.phase_number"),
                    phase_id=cls._string(item["phase_id"], "phase.phase_id"),
                    title=cls._string(item["title"], "phase.title"),
                    start_week=cls._integer(item["start_week"], "phase.start_week"),
                    end_week=cls._integer(item["end_week"], "phase.end_week"),
                    narrative_objective=cls._string(
                        item["narrative_objective"], "phase.narrative_objective"
                    ),
                    campaign_objective=cls._string(
                        item["campaign_objective"], "phase.campaign_objective"
                    ),
                    audience=cls._string(item["audience"], "phase.audience"),
                    tone=cls._string(item["tone"], "phase.tone"),
                    platforms=cls._strings(item["platforms"], "phase.platforms"),
                )
                for item in cls._objects(value["phases"], "plan.phases")
            ),
        )

    @classmethod
    def _treatment(cls, value: dict[str, object]) -> CinematicTreatment:
        return CinematicTreatment(
            work_id=cls._string(value["work_id"], "treatment.work_id"),
            work_name=cls._string(value["work_name"], "treatment.work_name"),
            concept=cls._string(value["concept"], "treatment.concept"),
            audience=cls._string(value["audience"], "treatment.audience"),
            platforms=cls._strings(value["platforms"], "treatment.platforms"),
            visual_motifs=cls._strings(value["visual_motifs"], "treatment.visual_motifs"),
            scenes=tuple(
                CinematicScene(
                    number=cls._integer(item["number"], "scene.number"),
                    phase_id=cls._string(item["phase_id"], "scene.phase_id"),
                    title=cls._string(item["title"], "scene.title"),
                    narrative_purpose=cls._string(
                        item["narrative_purpose"], "scene.narrative_purpose"
                    ),
                    setting=cls._string(item["setting"], "scene.setting"),
                    subjects=cls._strings(item["subjects"], "scene.subjects"),
                    motifs=cls._strings(item["motifs"], "scene.motifs"),
                    mood=cls._string(item["mood"], "scene.mood"),
                    shots=tuple(
                        ShotDirection(
                            number=cls._integer(shot["number"], "shot.number"),
                            framing=cls._string(shot["framing"], "shot.framing"),
                            movement=cls._string(shot["movement"], "shot.movement"),
                            description=cls._string(shot["description"], "shot.description"),
                        )
                        for shot in cls._objects(item["shots"], "scene.shots")
                    ),
                )
                for item in cls._objects(value["scenes"], "treatment.scenes")
            ),
        )

    @classmethod
    def _video_prompt(cls, value: dict[str, object]) -> VideoPrompt:
        return VideoPrompt(
            work_id=cls._string(value["work_id"], "video_prompt.work_id"),
            work_name=cls._string(value["work_name"], "video_prompt.work_name"),
            concept=cls._string(value["concept"], "video_prompt.concept"),
            audience=cls._string(value["audience"], "video_prompt.audience"),
            platforms=cls._strings(value["platforms"], "video_prompt.platforms"),
            scenes=tuple(
                VideoScenePrompt(
                    number=cls._integer(item["number"], "video_scene.number"),
                    phase_id=cls._string(item["phase_id"], "video_scene.phase_id"),
                    title=cls._string(item["title"], "video_scene.title"),
                    narrative_purpose=cls._string(
                        item["narrative_purpose"], "video_scene.narrative_purpose"
                    ),
                    shots=tuple(
                        VideoShotPrompt(
                            number=cls._integer(shot["number"], "video_shot.number"),
                            duration_seconds=cls._integer(
                                shot["duration_seconds"], "video_shot.duration_seconds"
                            ),
                            setting=cls._string(shot["setting"], "video_shot.setting"),
                            subjects=cls._strings(shot["subjects"], "video_shot.subjects"),
                            action=cls._string(shot["action"], "video_shot.action"),
                            framing=cls._string(shot["framing"], "video_shot.framing"),
                            movement=cls._string(shot["movement"], "video_shot.movement"),
                            mood=cls._string(shot["mood"], "video_shot.mood"),
                            motifs=cls._strings(shot["motifs"], "video_shot.motifs"),
                            continuity=cls._string(
                                shot["continuity"], "video_shot.continuity"
                            ),
                        )
                        for shot in cls._objects(item["shots"], "video_scene.shots")
                    ),
                )
                for item in cls._objects(value["scenes"], "video_prompt.scenes")
            ),
        )

    @classmethod
    def _image_plan(cls, value: dict[str, object]) -> ImagePlan:
        return ImagePlan(
            work_id=cls._string(value["work_id"], "image_plan.work_id"),
            work_name=cls._string(value["work_name"], "image_plan.work_name"),
            audience=cls._string(value["audience"], "image_plan.audience"),
            platforms=cls._strings(value["platforms"], "image_plan.platforms"),
            visual_direction=cls._string(
                value["visual_direction"], "image_plan.visual_direction"
            ),
            concepts=tuple(
                ImageConcept(
                    number=cls._integer(item["number"], "image_concept.number"),
                    phase_id=cls._string(item["phase_id"], "image_concept.phase_id"),
                    title=cls._string(item["title"], "image_concept.title"),
                    narrative_purpose=cls._string(
                        item["narrative_purpose"], "image_concept.narrative_purpose"
                    ),
                    setting=cls._string(item["setting"], "image_concept.setting"),
                    subjects=cls._strings(item["subjects"], "image_concept.subjects"),
                    identity_reference=cls._string(
                        item["identity_reference"], "image_concept.identity_reference"
                    ),
                    wardrobe=cls._string(item["wardrobe"], "image_concept.wardrobe"),
                    motifs=cls._strings(item["motifs"], "image_concept.motifs"),
                    mood=cls._string(item["mood"], "image_concept.mood"),
                    exclusions=cls._strings(item["exclusions"], "image_concept.exclusions"),
                    formats=tuple(
                        ImageFormat(
                            name=cls._string(image_format["name"], "image_format.name"),
                            aspect_ratio=cls._string(
                                image_format["aspect_ratio"], "image_format.aspect_ratio"
                            ),
                            composition=cls._string(
                                image_format["composition"], "image_format.composition"
                            ),
                            typography=cls._string(
                                image_format["typography"], "image_format.typography"
                            ),
                        )
                        for image_format in cls._objects(
                            item["formats"], "image_concept.formats"
                        )
                    ),
                )
                for item in cls._objects(value["concepts"], "image_plan.concepts")
            ),
        )

    @staticmethod
    def _object(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise TypeError(f"{field} must be an object")
        return value

    @classmethod
    def _objects(cls, value: object, field: str) -> tuple[dict[str, object], ...]:
        if not isinstance(value, list):
            raise TypeError(f"{field} must be a list")
        return tuple(cls._object(item, field) for item in value)

    @staticmethod
    def _string(value: object, field: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field} must be a string")
        return value

    @classmethod
    def _strings(cls, value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise TypeError(f"{field} must be a list")
        return tuple(cls._string(item, field) for item in value)

    @staticmethod
    def _integer(value: object, field: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{field} must be an integer")
        return value
