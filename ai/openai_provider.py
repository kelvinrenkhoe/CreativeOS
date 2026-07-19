"""OpenAI implementation of the CreativeOS AI provider."""

from openai import OpenAI

from .provider import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI AI provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.5",
    ) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        raise NotImplementedError("OpenAI generation not implemented yet.")
