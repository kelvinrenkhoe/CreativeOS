"""Deterministic provider used for tests and offline execution planning."""

from hashlib import sha256

from providers.base import AIExecutionProvider
from providers.models import (
    GenerationRequest,
    GenerationResult,
    MediaType,
    ProviderCapability,
    ProviderError,
)


_MEDIA_TYPES = {
    ProviderCapability.TEXT: MediaType.TEXT,
    ProviderCapability.IMAGE: MediaType.IMAGE,
    ProviderCapability.VIDEO: MediaType.VIDEO,
    ProviderCapability.VOICE: MediaType.AUDIO,
}


class MockProvider(AIExecutionProvider):
    """Return stable synthetic results without network or file side effects."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return tuple(ProviderCapability)

    def execute(self, request: GenerationRequest) -> GenerationResult:
        if not self.supports(request.capability):
            raise ProviderError(f"mock does not support {request.capability.value}")
        digest = sha256(
            f"{request.request_id}|{request.capability.value}|{request.prompt}".encode()
        ).hexdigest()[:16]
        model = request.model or f"mock-{request.capability.value}-v1"
        campaign = request.campaign_id or "none"
        content = (
            f"[MOCK {request.capability.value.upper()}]\n"
            f"Request: {request.request_id}\n"
            f"Campaign: {campaign}\n"
            f"Prompt hash: {digest}"
        )
        return GenerationResult(
            result_id=f"{request.request_id}-mock-result",
            request_id=request.request_id,
            provider_name=self.name,
            capability=request.capability,
            media_type=_MEDIA_TYPES[request.capability],
            content=content,
            model=model,
            metadata=(("prompt_hash", digest),),
        )
