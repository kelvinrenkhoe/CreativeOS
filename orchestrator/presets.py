"""Named, validated campaign runtime presets."""

from collections.abc import Mapping
from dataclasses import dataclass

from orchestrator.campaign_pipeline import PipelineRegistry
from orchestrator.models import PipelineError
from orchestrator.runtime import CampaignRuntimeBuilder, RuntimeStage, StageHandler


@dataclass(frozen=True, slots=True)
class CampaignRuntimePreset:
    """Describe a reusable campaign runtime stage graph."""

    name: str
    description: str
    required_context_keys: tuple[str, ...]
    stages: tuple[RuntimeStage, ...]

    def __post_init__(self) -> None:
        name = self.name.strip()
        description = self.description.strip()
        required_keys = tuple(key.strip() for key in self.required_context_keys)
        if not name:
            raise PipelineError("runtime preset name must not be empty")
        if not description:
            raise PipelineError("runtime preset description must not be empty")
        if not self.stages:
            raise PipelineError("runtime preset must contain at least one stage")
        if any(not key for key in required_keys):
            raise PipelineError("required context keys must not be empty")
        if len(required_keys) != len(set(required_keys)):
            raise PipelineError("required context keys must be unique")

        stage_names = tuple(stage.name for stage in self.stages)
        output_keys = tuple(stage.output_key for stage in self.stages)
        if len(stage_names) != len(set(stage_names)):
            raise PipelineError("runtime preset stage names must be unique")
        if len(output_keys) != len(set(output_keys)):
            raise PipelineError("runtime preset output keys must be unique")

        known_names = set(stage_names)
        for stage in self.stages:
            missing = sorted(set(stage.dependencies) - known_names)
            if missing:
                names = ", ".join(missing)
                raise PipelineError(
                    f"runtime preset stage {stage.name} has missing dependencies: {names}"
                )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "required_context_keys", required_keys)

    def build_registry(self) -> PipelineRegistry:
        """Build a pipeline registry for this preset."""

        return CampaignRuntimeBuilder(self.stages).build_registry()


class CampaignRuntimePresetRegistry:
    """Store uniquely named campaign runtime presets."""

    def __init__(self) -> None:
        self._presets: dict[str, CampaignRuntimePreset] = {}

    def register(self, preset: CampaignRuntimePreset) -> None:
        if preset.name in self._presets:
            raise PipelineError(f"runtime preset already registered: {preset.name}")
        self._presets[preset.name] = preset

    def get(self, name: str) -> CampaignRuntimePreset:
        try:
            return self._presets[name]
        except KeyError as error:
            raise PipelineError(f"runtime preset not found: {name}") from error

    def presets(self) -> tuple[CampaignRuntimePreset, ...]:
        return tuple(self._presets[name] for name in sorted(self._presets))


_MUSIC_RELEASE_STAGE_NAMES = (
    "brief",
    "storyboard",
    "captions",
    "image_prompts",
    "video_prompts",
    "voice_over",
    "press",
    "package",
    "publishing_manifest",
)


def music_release_preset(
    handlers: Mapping[str, StageHandler],
) -> CampaignRuntimePreset:
    """Build the standard music-release preset from supplied stage handlers."""

    missing = tuple(name for name in _MUSIC_RELEASE_STAGE_NAMES if name not in handlers)
    if missing:
        names = ", ".join(missing)
        raise PipelineError(f"music-release preset missing handlers: {names}")

    stages = (
        RuntimeStage("brief", handlers["brief"], ("campaign",), "brief"),
        RuntimeStage(
            "storyboard",
            handlers["storyboard"],
            ("brief",),
            "storyboard",
            dependencies=("brief",),
        ),
        RuntimeStage(
            "captions",
            handlers["captions"],
            ("brief", "storyboard"),
            "captions",
            dependencies=("brief", "storyboard"),
        ),
        RuntimeStage(
            "image_prompts",
            handlers["image_prompts"],
            ("brief", "storyboard"),
            "image_prompts",
            dependencies=("brief", "storyboard"),
        ),
        RuntimeStage(
            "video_prompts",
            handlers["video_prompts"],
            ("brief", "storyboard"),
            "video_prompts",
            dependencies=("brief", "storyboard"),
        ),
        RuntimeStage(
            "voice_over",
            handlers["voice_over"],
            ("brief", "storyboard"),
            "voice_over",
            dependencies=("brief", "storyboard"),
        ),
        RuntimeStage(
            "press",
            handlers["press"],
            ("brief",),
            "press",
            dependencies=("brief",),
        ),
        RuntimeStage(
            "package",
            handlers["package"],
            (
                "brief",
                "storyboard",
                "captions",
                "image_prompts",
                "video_prompts",
                "voice_over",
                "press",
            ),
            "package",
            dependencies=(
                "brief",
                "storyboard",
                "captions",
                "image_prompts",
                "video_prompts",
                "voice_over",
                "press",
            ),
        ),
        RuntimeStage(
            "publishing_manifest",
            handlers["publishing_manifest"],
            ("package",),
            "publishing_manifest",
            dependencies=("package",),
        ),
    )
    return CampaignRuntimePreset(
        name="music-release",
        description="Prepare a complete music-release campaign package and publishing manifest.",
        required_context_keys=("campaign",),
        stages=stages,
    )
