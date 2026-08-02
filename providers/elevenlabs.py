"""Non-executing ElevenLabs adapter placeholder."""

from providers.base import ProviderAdapterStub
from providers.models import ProviderCapability


class ElevenLabsProvider(ProviderAdapterStub):
    provider_name = "elevenlabs"
    supported_capabilities = (ProviderCapability.VOICE,)
