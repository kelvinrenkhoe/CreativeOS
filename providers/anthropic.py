"""Non-executing Anthropic adapter placeholder."""

from providers.base import ProviderAdapterStub
from providers.models import ProviderCapability


class AnthropicProvider(ProviderAdapterStub):
    provider_name = "anthropic"
    supported_capabilities = (ProviderCapability.TEXT,)
