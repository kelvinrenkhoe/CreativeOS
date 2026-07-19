"""Registry for available CreativeOS AI providers."""

from collections.abc import Callable

from ai.exceptions import UnknownProviderError
from ai.provider import AIProvider

ProviderFactory = Callable[..., AIProvider]


class ProviderRegistry:
    """Register and construct AI providers by stable name."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderFactory] = {}

    def register(self, name: str, factory: ProviderFactory) -> None:
        """Register a provider factory."""
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Provider name must not be empty.")
        self._providers[normalized_name] = factory

    def create(self, name: str, **kwargs: object) -> AIProvider:
        """Construct a registered provider."""
        normalized_name = name.strip().lower()
        try:
            factory = self._providers[normalized_name]
        except KeyError as exc:
            raise UnknownProviderError(f"Unknown AI provider: {name}") from exc
        return factory(**kwargs)

    def available(self) -> tuple[str, ...]:
        """Return registered provider names in deterministic order."""
        return tuple(sorted(self._providers))
