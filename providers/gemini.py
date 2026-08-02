"""Non-executing Gemini adapter placeholder."""

from providers.base import ProviderAdapterStub
from providers.models import ProviderCapability


class GeminiProvider(ProviderAdapterStub):
    provider_name = "gemini"
    supported_capabilities = (
        ProviderCapability.TEXT,
        ProviderCapability.IMAGE,
        ProviderCapability.VIDEO,
    )
