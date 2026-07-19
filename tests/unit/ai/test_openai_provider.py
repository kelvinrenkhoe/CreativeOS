"""Unit tests for the OpenAI provider."""

from unittest.mock import MagicMock, patch

import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from ai.exceptions import AIError
from ai.openai_provider import OpenAIProvider


def test_provider_name() -> None:
    provider = OpenAIProvider(api_key="test-key", model="gpt-5.5")
    assert provider.name == "openai"


def test_provider_model() -> None:
    provider = OpenAIProvider(api_key="test-key", model="gpt-5.5")
    assert provider.model == "gpt-5.5"


def test_empty_api_key() -> None:
    with pytest.raises(AIError):
        OpenAIProvider(api_key="", model="gpt-5.5")


def test_empty_model() -> None:
    with pytest.raises(AIError):
        OpenAIProvider(api_key="key", model="")


@patch("ai.openai_provider.OpenAI")
def test_generate_success(mock_openai: MagicMock) -> None:
    response = MagicMock()
    response.output_text = "Hello CreativeOS"

    client = MagicMock()
    client.responses.create.return_value = response
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    result = provider.generate("Hello")

    assert result == "Hello CreativeOS"
    client.responses.create.assert_called_once_with(
        model="gpt-5.5",
        input="Hello",
    )


@patch("ai.openai_provider.OpenAI")
def test_generate_with_optional_parameters(mock_openai: MagicMock) -> None:
    response = MagicMock()
    response.output_text = "Generated response"

    client = MagicMock()
    client.responses.create.return_value = response
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    result = provider.generate(
        "Write a caption",
        system_prompt="You are a music marketing assistant.",
        temperature=0.7,
        max_tokens=300,
    )

    assert result == "Generated response"
    client.responses.create.assert_called_once_with(
        model="gpt-5.5",
        input="Write a caption",
        instructions="You are a music marketing assistant.",
        temperature=0.7,
        max_output_tokens=300,
    )


@patch("ai.openai_provider.OpenAI")
def test_generate_empty_prompt(mock_openai: MagicMock) -> None:
    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(ValueError, match="Prompt must not be empty"):
        provider.generate("   ")


@patch("ai.openai_provider.OpenAI")
def test_invalid_temperature(mock_openai: MagicMock) -> None:
    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        provider.generate("Hello", temperature=2.1)


@patch("ai.openai_provider.OpenAI")
def test_invalid_max_tokens(mock_openai: MagicMock) -> None:
    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(ValueError, match="Maximum tokens must be greater than zero"):
        provider.generate("Hello", max_tokens=0)


@patch("ai.openai_provider.OpenAI")
def test_authentication_error(mock_openai: MagicMock) -> None:
    client = MagicMock()
    client.responses.create.side_effect = AuthenticationError(
        "bad key",
        response=MagicMock(),
        body=None,
    )
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(AIError, match="authentication failed"):
        provider.generate("Hello")


@patch("ai.openai_provider.OpenAI")
def test_rate_limit_error(mock_openai: MagicMock) -> None:
    client = MagicMock()
    client.responses.create.side_effect = RateLimitError(
        "rate limit",
        response=MagicMock(),
        body=None,
    )
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(AIError, match="rate limit"):
        provider.generate("Hello")


@patch("ai.openai_provider.OpenAI")
def test_connection_error(mock_openai: MagicMock) -> None:
    client = MagicMock()
    client.responses.create.side_effect = APIConnectionError(request=MagicMock())
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(AIError, match="could not connect"):
        provider.generate("Hello")


@patch("ai.openai_provider.OpenAI")
def test_timeout_error(mock_openai: MagicMock) -> None:
    client = MagicMock()
    client.responses.create.side_effect = APITimeoutError(request=MagicMock())
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(AIError, match="timed out"):
        provider.generate("Hello")


@patch("ai.openai_provider.OpenAI")
def test_empty_response(mock_openai: MagicMock) -> None:
    response = MagicMock()
    response.output_text = ""

    client = MagicMock()
    client.responses.create.return_value = response
    mock_openai.return_value = client

    provider = OpenAIProvider(api_key="key", model="gpt-5.5")

    with pytest.raises(AIError, match="empty response"):
        provider.generate("Hello")
