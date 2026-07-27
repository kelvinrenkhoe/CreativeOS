"""Execute approved image requests through the OpenAI Image API."""

import base64
import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from services.provider_configuration import (
    ProviderAdapterFactory,
    ProviderConfiguration,
    ProviderConfigurationError,
)
from services.provider_execution import ExecutionReceipt, ExecutionRequest
from services.queue_worker import RetryableProviderError


class OpenAIImageAdapter:
    """Generate images through one configured OpenAI client."""

    _SIZES = ("auto", "1024x1024", "1536x1024", "1024x1536")
    _QUALITIES = ("auto", "low", "medium", "high")
    _BACKGROUNDS = ("auto", "transparent", "opaque")
    _FORMATS = ("png", "jpeg", "webp")
    _PARAMETERS = ("size", "quality", "background", "output_format", "n")

    def __init__(
        self,
        client: Any,
        *,
        model: str,
        output_dir: Path,
    ) -> None:
        self._client = client
        self._model = self._required(model, "model")
        self._output_dir = output_dir

    @property
    def provider(self) -> str:
        """Return the provider handled by this adapter."""
        return "openai"

    @property
    def media_types(self) -> tuple[str, ...]:
        """Declare the adapter's image-only capability."""
        return ("image",)

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        """Return all provider-specific request validation errors."""
        errors: list[str] = []
        parameters = {item.name: item.value for item in request.parameters}

        unsupported = tuple(name for name in parameters if name not in self._PARAMETERS)
        if unsupported:
            errors.append(f"unsupported OpenAI image parameter: {unsupported[0]}")

        self._choice_error(parameters, "size", self._SIZES, errors)
        self._choice_error(parameters, "quality", self._QUALITIES, errors)
        self._choice_error(parameters, "background", self._BACKGROUNDS, errors)
        self._choice_error(parameters, "output_format", self._FORMATS, errors)

        if "n" in parameters:
            try:
                count = int(parameters["n"])
            except ValueError:
                errors.append("OpenAI image parameter n must be an integer")
            else:
                if not 1 <= count <= 4:
                    errors.append("OpenAI image parameter n must be between 1 and 4")

        return tuple(errors)

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        """Generate, persist, and describe one approved image request."""
        parameters = {item.name: item.value for item in request.parameters}
        call: dict[str, Any] = {
            "model": self._model,
            "prompt": request.prompt,
        }
        for name in self._PARAMETERS:
            if name in parameters:
                call[name] = int(parameters[name]) if name == "n" else parameters[name]

        try:
            response = self._client.images.generate(**call)
        except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError) as error:
            raise RetryableProviderError("OpenAI image generation temporarily failed") from error
        except APIStatusError as error:
            raise RuntimeError("OpenAI image generation failed") from error

        data = tuple(getattr(response, "data", ()) or ())
        if not data:
            raise RuntimeError("OpenAI image generation returned no outputs")

        output_format = parameters.get("output_format", "png")
        request_key = hashlib.sha256(request.request_id.encode()).hexdigest()[:16]
        self._output_dir.mkdir(parents=True, exist_ok=True)

        outputs = []
        for index, item in enumerate(data, start=1):
            encoded = getattr(item, "b64_json", None)
            if not encoded:
                raise RuntimeError("OpenAI image generation returned an invalid output")
            try:
                image = base64.b64decode(encoded, validate=True)
            except ValueError as error:
                raise RuntimeError("OpenAI image generation returned an invalid output") from error

            path = self._output_dir / f"{request_key}-{index}.{output_format}"
            temporary = path.with_suffix(f"{path.suffix}.tmp")
            temporary.write_bytes(image)
            temporary.replace(path)
            outputs.append(str(path.resolve()))

        created = getattr(response, "created", None)
        external_id = f"openai-image:{created or request.request_id}"
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id=external_id,
            outputs=tuple(outputs),
        )

    @staticmethod
    def _choice_error(
        parameters: dict[str, str],
        name: str,
        allowed: tuple[str, ...],
        errors: list[str],
    ) -> None:
        if name in parameters and parameters[name] not in allowed:
            errors.append(f"unsupported OpenAI image {name}: {parameters[name]}")

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ProviderConfigurationError(f"OpenAI image {field} must not be empty")
        return normalized


class OpenAIImageAdapterFactory(ProviderAdapterFactory):
    """Construct an image adapter without exposing its credential."""

    def __init__(self, client_factory: Callable[..., Any] = OpenAI) -> None:
        self._client_factory = client_factory

    @property
    def provider(self) -> str:
        """Return the normalized factory provider."""
        return "openai"

    def create(
        self,
        configuration: ProviderConfiguration,
        credential: str,
    ) -> OpenAIImageAdapter:
        """Create a configured OpenAI image adapter."""
        if "image" not in configuration.media_types:
            raise ProviderConfigurationError("OpenAI image capability is not configured")

        options = {item.name: item.value for item in configuration.options}
        unsupported = tuple(name for name in options if name != "output_dir")
        if unsupported:
            raise ProviderConfigurationError(
                f"unsupported OpenAI image configuration option: {unsupported[0]}"
            )

        client_options: dict[str, Any] = {
            "api_key": credential,
            "timeout": configuration.timeout_seconds,
        }
        if configuration.endpoint:
            client_options["base_url"] = configuration.endpoint

        client = self._client_factory(**client_options)
        return OpenAIImageAdapter(
            client,
            model=configuration.model or "gpt-image-2",
            output_dir=Path(options.get("output_dir", ".creativeos/generated/images")),
        )
