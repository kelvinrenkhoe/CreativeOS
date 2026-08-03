"""Tests for named campaign runtime presets."""

import pytest

from orchestrator import (
    CampaignExecutionEngine,
    CampaignRuntimePreset,
    CampaignRuntimePresetRegistry,
    ExecutionContext,
    PipelineError,
    RuntimeStage,
    music_release_preset,
)


def _handlers():
    return {
        "brief": lambda campaign: f"brief:{campaign}",
        "storyboard": lambda brief: f"storyboard:{brief}",
        "captions": lambda brief, storyboard: f"captions:{brief}|{storyboard}",
        "image_prompts": lambda brief, storyboard: f"images:{brief}|{storyboard}",
        "video_prompts": lambda brief, storyboard: f"videos:{brief}|{storyboard}",
        "voice_over": lambda brief, storyboard: f"voice:{brief}|{storyboard}",
        "press": lambda brief: f"press:{brief}",
        "package": lambda *values: f"package:{len(values)}",
        "publishing_manifest": lambda package: f"manifest:{package}",
    }


def _clock():
    current = -1

    def tick() -> int:
        nonlocal current
        current += 1
        return current

    return tick


def test_music_release_preset_executes_complete_runtime() -> None:
    preset = music_release_preset(_handlers())
    context = ExecutionContext("no-lose-guard")
    context.set("campaign", "No Lose Guard")

    report = CampaignExecutionEngine(
        preset.build_registry(),
        clock=_clock(),
    ).run(context)

    assert report.succeeded is True
    assert report.completed_stages == (
        "brief",
        "press",
        "storyboard",
        "captions",
        "image_prompts",
        "video_prompts",
        "voice_over",
        "package",
        "publishing_manifest",
    )
    assert context.get("publishing_manifest") == "manifest:package:7"


def test_preset_registry_lists_names_deterministically() -> None:
    registry = CampaignRuntimePresetRegistry()
    music = music_release_preset(_handlers())
    book = CampaignRuntimePreset(
        name="book-launch",
        description="Prepare a book launch.",
        required_context_keys=("campaign",),
        stages=(RuntimeStage("brief", lambda campaign: campaign, ("campaign",), "brief"),),
    )

    registry.register(music)
    registry.register(book)

    assert tuple(preset.name for preset in registry.presets()) == (
        "book-launch",
        "music-release",
    )
    assert registry.get("music-release") is music


def test_preset_registry_rejects_unknown_name() -> None:
    with pytest.raises(PipelineError, match="runtime preset not found"):
        CampaignRuntimePresetRegistry().get("missing")


def test_music_release_preset_requires_all_handlers() -> None:
    handlers = _handlers()
    del handlers["press"]

    with pytest.raises(PipelineError, match="missing handlers: press"):
        music_release_preset(handlers)


def test_preset_rejects_duplicate_output_keys() -> None:
    stages = (
        RuntimeStage("brief", lambda campaign: campaign, ("campaign",), "result"),
        RuntimeStage("press", lambda brief: brief, ("result",), "result", ("brief",)),
    )

    with pytest.raises(PipelineError, match="output keys must be unique"):
        CampaignRuntimePreset(
            name="invalid",
            description="Invalid preset.",
            required_context_keys=("campaign",),
            stages=stages,
        )


def test_preset_rejects_missing_stage_dependency() -> None:
    stage = RuntimeStage(
        "captions",
        lambda brief: brief,
        ("brief",),
        "captions",
        dependencies=("brief",),
    )

    with pytest.raises(PipelineError, match="missing dependencies: brief"):
        CampaignRuntimePreset(
            name="invalid",
            description="Invalid preset.",
            required_context_keys=("campaign",),
            stages=(stage,),
        )
