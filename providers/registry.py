"""Deterministic provider registration and capability defaults."""

from providers.base import AIExecutionProvider
from providers.models import ProviderCapability, ProviderError


class ProviderRegistry:
    """Register providers and resolve explicit or default capability handlers."""

    def __init__(self) -> None:
        self._providers: dict[str, AIExecutionProvider] = {}
        self._defaults: dict[ProviderCapability, str] = {}

    def register(self, provider: AIExecutionProvider, *, replace: bool = False) -> None:
        name = provider.name.strip()
        if not name:
            raise ProviderError("provider name must be non-empty")
        if name in self._providers and not replace:
            raise ProviderError(f"provider already registered: {name}")
        self._providers[name] = provider

    def unregister(self, name: str) -> AIExecutionProvider:
        normalized = name.strip()
        if normalized not in self._providers:
            raise ProviderError(f"provider is not registered: {normalized}")
        provider = self._providers.pop(normalized)
        self._defaults = {
            capability: provider_name
            for capability, provider_name in self._defaults.items()
            if provider_name != normalized
        }
        return provider

    def get(self, name: str) -> AIExecutionProvider:
        normalized = name.strip()
        try:
            return self._providers[normalized]
        except KeyError as error:
            raise ProviderError(f"provider is not registered: {normalized}") from error

    def available(self, capability: ProviderCapability | None = None) -> tuple[str, ...]:
        names = (
            name
            for name, provider in self._providers.items()
            if capability is None or provider.supports(capability)
        )
        return tuple(sorted(names))

    def set_default(self, capability: ProviderCapability, name: str) -> None:
        provider = self.get(name)
        if not provider.supports(capability):
            raise ProviderError(
                f"provider {provider.name} does not support {capability.value} generation"
            )
        self._defaults[capability] = provider.name

    def default(self, capability: ProviderCapability) -> AIExecutionProvider:
        try:
            provider_name = self._defaults[capability]
        except KeyError as error:
            raise ProviderError(f"no default provider for {capability.value}") from error
        return self.get(provider_name)
