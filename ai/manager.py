"""Provider selection and construction for CreativeOS AI features."""

from ai.mock import MockProvider
from ai.provider import AIProvider
from ai.registry import ProviderRegistry
from models.config import AIConfig


class AIManager:
    """Resolve configured AI providers through a registry."""

    def __init__(
        self,
        config: AIConfig | None = None,
        registry: ProviderRegistry | None = None,
    ) -> None:
        self.config = config or AIConfig(provider="mock", default_model="mock-v1")
        self.registry = registry or ProviderRegistry()
        if "mock" not in self.registry.available():
            self.registry.register("mock", MockProvider)

    @property
    def provider_name(self) -> str:
        """Return the configured provider, defaulting to mock."""
        return self.config.provider.strip().lower() or "mock"

    def available(self) -> tuple[str, ...]:
        """Return all registered provider names."""
        return self.registry.available()

    def get(self, name: str, *, model: str = "") -> AIProvider:
        """Construct a provider by name."""
        kwargs: dict[str, object] = {}
        if model:
            kwargs["model"] = model
        return self.registry.create(name, **kwargs)

    def default(self) -> AIProvider:
        """Construct the configured default provider."""
        return self.get(self.provider_name, model=self.config.default_model)
