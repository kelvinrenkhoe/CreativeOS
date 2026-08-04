"""Deterministic in-memory provider adapter for safe runtime testing."""

from hashlib import sha256

from services.provider_execution import ExecutionReceipt, ExecutionRequest


class InMemoryProviderExecutionAdapter:
    """Execute image and video requests without network or filesystem access."""

    def __init__(
        self,
        *,
        provider: str = "in-memory",
        media_types: tuple[str, ...] = ("image", "video"),
    ) -> None:
        self._provider = self._required(provider, "provider").casefold()
        self._media_types = tuple(
            self._required(media_type, "media_type").casefold() for media_type in media_types
        )
        if not self._media_types:
            raise ValueError("media_types must not be empty")
        if len(self._media_types) != len(set(self._media_types)):
            raise ValueError("media_types must be unique")
        self._requests: dict[str, ExecutionRequest] = {}
        self._receipts: dict[str, ExecutionReceipt] = {}

    @property
    def provider(self) -> str:
        """Return the normalized provider name handled by this adapter."""
        return self._provider

    @property
    def media_types(self) -> tuple[str, ...]:
        """Return the normalized media types supported by this adapter."""
        return self._media_types

    @property
    def receipts(self) -> tuple[ExecutionReceipt, ...]:
        """Return executed receipts in deterministic request-ID order."""
        return tuple(self._receipts[key] for key in sorted(self._receipts))

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        """Return deterministic validation errors without changing state."""
        errors: list[str] = []
        if request.provider.strip().casefold() != self.provider:
            errors.append("request provider is not supported")
        if request.media_type.strip().casefold() not in self.media_types:
            errors.append("request media_type is not supported")
        if request.request_id in self._requests and self._requests[request.request_id] != request:
            errors.append("request_id is already associated with different work")
        return tuple(errors)

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        """Return a stable receipt and replay identical requests idempotently."""
        errors = self.validate(request)
        if errors:
            raise ValueError(f"in-memory provider validation failed: {'; '.join(errors)}")

        existing = self._receipts.get(request.request_id)
        if existing is not None:
            return existing

        external_id = self._external_id(request)
        output = f"memory://{self.provider}/{request.media_type}/{external_id}"
        receipt = ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id=external_id,
            outputs=(output,),
        )
        self._requests[request.request_id] = request
        self._receipts[request.request_id] = receipt
        return receipt

    def receipt(self, request_id: str) -> ExecutionReceipt | None:
        """Return a previously executed receipt by request ID."""
        return self._receipts.get(self._required(request_id, "request_id"))

    @staticmethod
    def _external_id(request: ExecutionRequest) -> str:
        parameters = "|".join(f"{item.name}={item.value}" for item in request.parameters)
        identity = "|".join(
            (
                request.request_id,
                request.asset_id,
                request.work_id,
                request.media_type,
                request.provider,
                request.prompt,
                parameters,
            )
        )
        return f"memory-{sha256(identity.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
