"""OpenAI implementation of the CreativeOS AI provider."""

from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from ai.exceptions import AIError
from ai.provider import AIProvider


class OpenAIProvider(AIProvider):
    """Generate text using the OpenAI Responses API."""

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        if not api_key.strip():
            raise AIError(
                "OPENAI_API_KEY is not configured. "
                "Set it in your environment before using the OpenAI provider."
            )

        if not model.strip():
            raise AIError("OpenAI model must not be empty.")

        self._model = model.strip()
        self._client = OpenAI(api_key=api_key.strip())

    @property
    def name(self) -> str:
        """Return the provider's stable registry name."""
        return "openai"

    @property
    def model(self) -> str:
        """Return the configured OpenAI model."""
        return self._model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text using the OpenAI Responses API."""
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            raise ValueError("Prompt must not be empty.")

        request: dict[str, Any] = {
            "model": self._model,
            "input": cleaned_prompt,
        }

        if system_prompt and system_prompt.strip():
            request["instructions"] = system_prompt.strip()

        if temperature is not None:
            if not 0 <= temperature <= 2:
                raise ValueError("Temperature must be between 0 and 2.")
            request["temperature"] = temperature

        if max_tokens is not None:
            if max_tokens <= 0:
                raise ValueError("Maximum tokens must be greater than zero.")
            request["max_output_tokens"] = max_tokens

        try:
            response = self._client.responses.create(**request)
        except AuthenticationError as exc:
            raise AIError("OpenAI authentication failed. Check OPENAI_API_KEY.") from exc
        except RateLimitError as exc:
            raise AIError("OpenAI rate limit or usage limit was reached. Try again later.") from exc
        except APITimeoutError as exc:
            raise AIError("The OpenAI request timed out.") from exc
        except APIConnectionError as exc:
            raise AIError("CreativeOS could not connect to OpenAI.") from exc
        except APIError as exc:
            raise AIError(f"OpenAI API request failed: {exc}") from exc

        output = response.output_text
        if not output or not output.strip():
            raise AIError("OpenAI returned an empty response.")

        return output.strip()
