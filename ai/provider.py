"""Abstract interface implemented by CreativeOS AI providers."""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Common interface for text-generation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider's stable registry name."""

    @property
    def model(self) -> str:
        """Return the configured model name when applicable."""
        return ""

    @abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None) -> str:
        """Generate text from a prompt."""
