"""Tests for provider-neutral AI execution core."""

import pytest

from providers.anthropic import AnthropicProvider
from providers.elevenlabs import ElevenLabsProvider
from providers.gemini import GeminiProvider
from providers.mock import MockProvider
from providers.models import GenerationRequest, MediaType, ProviderCapability, ProviderError
from providers.openai import OpenAIProvider
from providers.registry import ProviderRegistry


def request(
    capability: ProviderCapability = ProviderCapability.TEXT,
    **overrides,
) -> GenerationRequest:
    values = {
        "request_id": "no-lose-guard-week-3-text",
        "capability": capability,
        "prompt": "Create a campaign-aligned asset.",
        "campaign_id": "no-lose-guard",
    }
    values.update(overrides)
    return GenerationRequest(**values)


def test_mock_provider_is_stable_for_every_capability() -> None:
    provider = MockProvider()

    first = tuple(provider.execute(request(capability)) for capability in ProviderCapability)
    second = tuple(provider.execute(request(capability)) for capability in ProviderCapability)

    assert first == second
    assert tuple(result.media_type for result in first) == (
        MediaType.TEXT,
        MediaType.IMAGE,
        MediaType.VIDEO,
        MediaType.AUDIO,
    )
    assert all(result.provider_name == "mock" for result in first)
    assert all("Prompt hash:" in result.content for result in first)


def test_registry_resolves_sorted_availability_and_defaults() -> None:
    registry = ProviderRegistry()
    registry.register(OpenAIProvider())
    registry.register(MockProvider())
    registry.register(AnthropicProvider())
    registry.set_default(ProviderCapability.TEXT, "mock")

    assert registry.available() == ("anthropic", "mock", "openai")
    assert registry.available(ProviderCapability.IMAGE) == ("mock", "openai")
    assert registry.default(ProviderCapability.TEXT).name == "mock"


def test_registry_rejects_duplicates_and_unsupported_defaults() -> None:
    registry = ProviderRegistry()
    registry.register(AnthropicProvider())

    with pytest.raises(ProviderError, match="already registered"):
        registry.register(AnthropicProvider())
    with pytest.raises(ProviderError, match="does not support voice"):
        registry.set_default(ProviderCapability.VOICE, "anthropic")


def test_unregister_removes_provider_and_its_defaults() -> None:
    registry = ProviderRegistry()
    registry.register(MockProvider())
    registry.set_default(ProviderCapability.VIDEO, "mock")

    removed = registry.unregister("mock")

    assert removed.name == "mock"
    assert registry.available() == ()
    with pytest.raises(ProviderError, match="no default provider"):
        registry.default(ProviderCapability.VIDEO)


def test_adapter_stubs_expose_capabilities_without_external_execution() -> None:
    providers = (
        OpenAIProvider(),
        GeminiProvider(),
        AnthropicProvider(),
        ElevenLabsProvider(),
    )

    assert OpenAIProvider().supports(ProviderCapability.IMAGE)
    assert GeminiProvider().supports(ProviderCapability.VIDEO)
    assert AnthropicProvider().supports(ProviderCapability.TEXT)
    assert ElevenLabsProvider().supports(ProviderCapability.VOICE)

    for provider in providers:
        capability = next(iter(provider.capabilities))
        with pytest.raises(ProviderError, match="not configured"):
            provider.execute(request(capability))


def test_request_validation_rejects_empty_prompt() -> None:
    with pytest.raises(ProviderError, match="prompt must be a non-empty string"):
        request(prompt="  ")
