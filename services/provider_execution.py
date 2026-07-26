"""Define safe, provider-neutral media execution contracts."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExecutionParameter:
    """One immutable provider option attached to an execution request."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """An approved image or video asset prepared for provider execution."""

    request_id: str
    asset_id: str
    work_id: str
    media_type: str
    provider: str
    prompt: str
    parameters: tuple[ExecutionParameter, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionApproval:
    """Explicit human authorization for one asset and execution target."""

    asset_id: str
    media_type: str
    provider: str
    approved_by: str


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Provider-neutral evidence returned after an adapter accepts a request."""

    request_id: str
    asset_id: str
    media_type: str
    provider: str
    external_id: str
    outputs: tuple[str, ...] = ()


class ProviderExecutionAdapter(Protocol):
    """Contract implemented by an image or video generation provider."""

    @property
    def provider(self) -> str:
        """Return the normalized provider handled by this adapter."""
        ...

    @property
    def media_types(self) -> tuple[str, ...]:
        """Return the normalized media types supported by this adapter."""
        ...

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        """Return provider-specific validation errors without executing."""
        ...

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        """Execute one already validated and approved request."""
        ...


class ProviderExecutionService:
    """Guard approval and hand one exact request to a provider adapter."""

    _MEDIA_TYPES = ("image", "video")

    def execute(
        self,
        request: ExecutionRequest,
        approval: ExecutionApproval,
        adapter: ProviderExecutionAdapter,
    ) -> ExecutionReceipt:
        """Execute only after common, approval, capability, and adapter validation."""
        normalized = self._validate_request(request)
        self._validate_approval(normalized, approval)
        self._validate_adapter(normalized, adapter)

        errors = adapter.validate(normalized)
        if errors:
            raise ValueError(f"provider validation failed: {'; '.join(errors)}")

        receipt = adapter.execute(normalized)
        self._validate_receipt(normalized, receipt)
        return receipt

    @classmethod
    def _validate_request(cls, request: ExecutionRequest) -> ExecutionRequest:
        media_type = cls._required(request.media_type, "media_type").casefold()
        if media_type not in cls._MEDIA_TYPES:
            raise ValueError(f"unsupported media_type: {media_type}")

        parameters = tuple(
            ExecutionParameter(
                name=cls._required(item.name, "parameter name").casefold(),
                value=cls._required(item.value, "parameter value"),
            )
            for item in request.parameters
        )
        names = tuple(item.name for item in parameters)
        if len(names) != len(set(names)):
            raise ValueError("execution parameter names must be unique")

        return ExecutionRequest(
            request_id=cls._required(request.request_id, "request_id"),
            asset_id=cls._required(request.asset_id, "asset_id"),
            work_id=cls._required(request.work_id, "work_id"),
            media_type=media_type,
            provider=cls._required(request.provider, "provider").casefold(),
            prompt=cls._required(request.prompt, "prompt"),
            parameters=parameters,
        )

    @classmethod
    def _validate_approval(
        cls,
        request: ExecutionRequest,
        approval: ExecutionApproval,
    ) -> None:
        approved_asset = cls._required(approval.asset_id, "approval asset_id")
        approved_media = cls._required(approval.media_type, "approval media_type").casefold()
        approved_provider = cls._required(approval.provider, "approval provider").casefold()
        cls._required(approval.approved_by, "approved_by")

        if (
            approved_asset != request.asset_id
            or approved_media != request.media_type
            or approved_provider != request.provider
        ):
            raise PermissionError("approval does not match execution request")

    @staticmethod
    def _validate_adapter(
        request: ExecutionRequest,
        adapter: ProviderExecutionAdapter,
    ) -> None:
        provider = adapter.provider.strip().casefold()
        media_types = tuple(item.strip().casefold() for item in adapter.media_types)
        if provider != request.provider:
            raise ValueError("execution adapter does not support request provider")
        if request.media_type not in media_types:
            raise ValueError("execution adapter does not support request media_type")

    @classmethod
    def _validate_receipt(
        cls,
        request: ExecutionRequest,
        receipt: ExecutionReceipt,
    ) -> None:
        identity = (
            receipt.request_id.strip() == request.request_id
            and receipt.asset_id.strip() == request.asset_id
            and receipt.media_type.strip().casefold() == request.media_type
            and receipt.provider.strip().casefold() == request.provider
        )
        if not identity:
            raise ValueError("execution receipt does not match request")
        cls._required(receipt.external_id, "receipt external_id")
        for output in receipt.outputs:
            cls._required(output, "receipt output")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
