"""Tests for the CreativeOS AI provider framework."""

import pytest

from ai.exceptions import UnknownProviderError
from ai.manager import AIManager
from ai.mock import MockProvider
from ai.registry import ProviderRegistry
from models.config import AIConfig


def test_mock_provider_generates_deterministic_response() -> None:
    provider = MockProvider()

    assert provider.name == "mock"
    assert provider.model == "mock-v1"
    assert provider.generate("Hello CreativeOS") == "Mock response"


def test_mock_provider_rejects_empty_prompt() -> None:
    provider = MockProvider()

    with pytest.raises(ValueError, match="Prompt must not be empty"):
        provider.generate("   ")


def test_registry_registers_and_creates_provider() -> None:
    registry = ProviderRegistry()
    registry.register("mock", MockProvider)

    provider = registry.create("MOCK", model="test-model")

    assert isinstance(provider, MockProvider)
    assert provider.model == "test-model"
    assert registry.available() == ("mock",)


def test_registry_rejects_unknown_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(UnknownProviderError, match="Unknown AI provider"):
        registry.create("missing")


def test_manager_defaults_to_mock_provider() -> None:
    provider = AIManager().default()

    assert provider.name == "mock"
    assert provider.model == "mock-v1"


def test_manager_uses_configured_model() -> None:
    config = AIConfig(provider="mock", default_model="campaign-test")

    provider = AIManager(config).default()

    assert provider.model == "campaign-test"
