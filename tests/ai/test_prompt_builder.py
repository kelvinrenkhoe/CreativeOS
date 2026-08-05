"""Tests for deterministic AI prompt construction."""

import pytest

from ai.prompts import PromptBuilder, PromptValidationError


def test_builder_chaining_returns_same_instance() -> None:
    builder = PromptBuilder()

    assert builder.system("System") is builder
    assert builder.instruction("Instruction") is builder
    assert builder.context("Context") is builder
    assert builder.constraint("Constraint") is builder


def test_render_requires_system_prompt() -> None:
    builder = PromptBuilder().instruction("Create a plan")

    with pytest.raises(PromptValidationError, match="system prompt is required"):
        builder.render()


def test_render_requires_instruction() -> None:
    builder = PromptBuilder().system("You are a strategist")

    with pytest.raises(PromptValidationError, match="instruction is required"):
        builder.render()


def test_empty_sections_are_rejected() -> None:
    builder = PromptBuilder()

    with pytest.raises(PromptValidationError, match="context must not be empty"):
        builder.context("   ")


def test_system_prompt_is_available_separately() -> None:
    builder = PromptBuilder().system("You are a strategist")

    assert builder.system_prompt == "You are a strategist"


def test_render_includes_instruction_context_and_constraints() -> None:
    prompt = (
        PromptBuilder()
        .system("You are a strategist")
        .instruction("Create a campaign plan")
        .context("Campaign: No Lose Guard")
        .constraint("Return JSON only")
        .render()
    )

    assert prompt == (
        "## Instruction\nCreate a campaign plan\n\n"
        "## Context\nCampaign: No Lose Guard\n\n"
        "## Constraints\n- Return JSON only"
    )


def test_multiple_context_items_preserve_insertion_order() -> None:
    prompt = (
        PromptBuilder()
        .system("System")
        .instruction("Instruction")
        .context("Artist: Kelvin Rankie")
        .context("Campaign: No Lose Guard")
        .render()
    )

    assert prompt.index("Artist: Kelvin Rankie") < prompt.index("Campaign: No Lose Guard")


def test_multiple_constraints_render_as_bullets() -> None:
    prompt = (
        PromptBuilder()
        .system("System")
        .instruction("Instruction")
        .constraint("Return JSON only")
        .constraint("Do not include Markdown")
        .render()
    )

    assert "- Return JSON only" in prompt
    assert "- Do not include Markdown" in prompt


def test_whitespace_is_normalised() -> None:
    builder = PromptBuilder().system("  You are   a strategist  ").instruction(
        " Create   a plan "
    )

    assert builder.system_prompt == "You are a strategist"
    assert "Create a plan" in builder.render()


def test_repeated_rendering_is_deterministic() -> None:
    builder = (
        PromptBuilder()
        .system("System")
        .instruction("Instruction")
        .context("Context")
        .constraint("Constraint")
    )

    assert builder.render() == builder.render()
