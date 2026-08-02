"""Provider contracts shared by concrete AI execution adapters."""

from abc import ABC, abstractmethod
from collections.abc import Collection

from providers.models import GenerationRequest, GenerationResult, ProviderCapability, ProviderError


class AIExecutionProvider(ABC):
    """Provider-neutral execution interface for generated creative intent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider's stable registry name."""

    @property
    @abstractmethod
    def capabilities(self) -> Collection[ProviderCapability]:
        """Return the capabilities supported by this provider."""

    @abstractmethod
    def execute(self, request: GenerationRequest) -> GenerationResult:
        """Execute one provider-neutral generation request."""

    def supports(self, capability: ProviderCapability) -> bool:
        return capability in self.capabilities


class ProviderAdapterStub(AIExecutionProvider):
    """Non-executing placeholder for a future external provider adapter."""

    provider_name = "stub"
    supported_capabilities: tuple[ProviderCapability, ...] = ()

    @property
    def name(self) -> str:
        return self.provider_name

    @property
    def capabilities(self) -> Collection[ProviderCapability]:
        return self.supported_capabilities

    def execute(self, request: GenerationRequest) -> GenerationResult:
        if not self.supports(request.capability):
            raise ProviderError(
                f"provider {self.name} does not support {request.capability.value} generation"
            )
        raise ProviderError(f"provider {self.name} is not configured for external execution")
