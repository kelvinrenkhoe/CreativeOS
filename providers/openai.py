"""Non-executing OpenAI adapter placeholder."""

from providers.base import ProviderAdapterStub
from providers.models import ProviderCapability


class OpenAIProvider(ProviderAdapterStub):
    provider_name = "openai"
    supported_capabilities = (
        ProviderCapability.TEXT,
        ProviderCapability.IMAGE,
        ProviderCapability.VOICE,
    )
