"""Immutable models for provider-neutral AI execution."""

from dataclasses import dataclass
from enum import StrEnum


class ProviderError(ValueError):
    """Reject invalid provider configuration or execution requests."""


class ProviderCapability(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"


class MediaType(StrEnum):
    TEXT = "text/plain"
    IMAGE = "image/mock"
    VIDEO = "video/mock"
    AUDIO = "audio/mock"


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    request_id: str
    capability: ProviderCapability
    prompt: str
    campaign_id: str | None = None
    model: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("request_id", "prompt"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ProviderError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        if self.campaign_id is not None:
            campaign_id = self.campaign_id.strip()
            if not campaign_id:
                raise ProviderError("campaign_id must be non-empty when provided")
            object.__setattr__(self, "campaign_id", campaign_id)
        if self.model is not None:
            model = self.model.strip()
            if not model:
                raise ProviderError("model must be non-empty when provided")
            object.__setattr__(self, "model", model)
        if any(not key.strip() or not value.strip() for key, value in self.metadata):
            raise ProviderError("metadata keys and values must be non-empty")


@dataclass(frozen=True, slots=True)
class GenerationResult:
    result_id: str
    request_id: str
    provider_name: str
    capability: ProviderCapability
    media_type: MediaType
    content: str
    model: str
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "result_id",
            "request_id",
            "provider_name",
            "content",
            "model",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ProviderError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
