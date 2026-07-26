"""Define safe, provider-neutral publishing contracts and orchestration."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PublicationRequest:
    """Content and destination metadata prepared for human review."""

    asset_id: str
    platform: str
    content: str
    media: tuple[str, ...] = ()
    scheduled_for: str | None = None


@dataclass(frozen=True, slots=True)
class PublicationApproval:
    """Explicit human authorization for one exact publication request."""

    asset_id: str
    platform: str
    approved_by: str


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    """Provider-neutral result returned after an adapter accepts a request."""

    platform: str
    external_id: str
    url: str | None = None


class PublishingAdapter(Protocol):
    """Contract implemented by a platform-specific publishing integration."""

    @property
    def platform(self) -> str:
        """Return the normalized platform handled by this adapter."""
        ...

    def validate(self, request: PublicationRequest) -> tuple[str, ...]:
        """Return provider-specific validation errors without publishing."""
        ...

    def publish(self, request: PublicationRequest) -> PublicationReceipt:
        """Publish an already validated and approved request."""
        ...


class PublishingService:
    """Validate approval and safely hand a request to a publishing adapter."""

    def publish(
        self,
        request: PublicationRequest,
        approval: PublicationApproval,
        adapter: PublishingAdapter,
    ) -> PublicationReceipt:
        """Publish only after common, approval, and adapter validation pass."""
        normalized = self._validate_request(request)
        self._validate_approval(normalized, approval)
        self._validate_adapter(normalized, adapter)

        errors = adapter.validate(normalized)
        if errors:
            raise ValueError(f"publication validation failed: {'; '.join(errors)}")

        receipt = adapter.publish(normalized)
        if receipt.platform.strip().casefold() != normalized.platform:
            raise ValueError("publication receipt platform does not match request")
        if not receipt.external_id.strip():
            raise ValueError("publication receipt external_id must not be empty")
        return receipt

    @classmethod
    def _validate_request(cls, request: PublicationRequest) -> PublicationRequest:
        return PublicationRequest(
            asset_id=cls._required(request.asset_id, "asset_id"),
            platform=cls._required(request.platform, "platform").casefold(),
            content=cls._required(request.content, "content"),
            media=tuple(cls._required(item, "media item") for item in request.media),
            scheduled_for=request.scheduled_for.strip() if request.scheduled_for else None,
        )

    @classmethod
    def _validate_approval(
        cls,
        request: PublicationRequest,
        approval: PublicationApproval,
    ) -> None:
        approved_asset = cls._required(approval.asset_id, "approval asset_id")
        approved_platform = cls._required(approval.platform, "approval platform").casefold()
        cls._required(approval.approved_by, "approved_by")

        if approved_asset != request.asset_id or approved_platform != request.platform:
            raise PermissionError("approval does not match publication request")

    @staticmethod
    def _validate_adapter(
        request: PublicationRequest,
        adapter: PublishingAdapter,
    ) -> None:
        if adapter.platform.strip().casefold() != request.platform:
            raise ValueError("publishing adapter does not support request platform")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
