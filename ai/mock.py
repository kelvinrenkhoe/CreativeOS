"""Offline AI provider used by tests and local development."""

from ai.provider import AIProvider


class MockProvider(AIProvider):
    """Return deterministic responses without network access."""

    def __init__(self, model: str = "mock-v1", response: str = "Mock response") -> None:
        self._model = model
        self._response = response

    @property
    def name(self) -> str:
        """Return the provider registry name."""
        return "mock"

    @property
    def model(self) -> str:
        """Return the configured mock model."""
        return self._model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Return the configured deterministic response."""
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        return self._response
