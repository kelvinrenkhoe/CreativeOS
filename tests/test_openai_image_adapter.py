import base64
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from services.openai_image_adapter import (
    OpenAIImageAdapter,
    OpenAIImageAdapterFactory,
)
from services.provider_configuration import (
    ProviderConfiguration,
    ProviderConfigurationService,
    ProviderOption,
)
from services.provider_execution import (
    ExecutionApproval,
    ExecutionParameter,
    ExecutionRequest,
    ProviderExecutionService,
)
from services.queue_worker import RetryableProviderError


@dataclass
class FakeImages:
    response: Any = None
    error: Exception | None = None
    received: dict[str, Any] | None = None

    def generate(self, **request: Any) -> Any:
        self.received = request
        if self.error:
            raise self.error
        return self.response


@dataclass
class FakeClient:
    images: FakeImages


def request(*parameters: ExecutionParameter) -> ExecutionRequest:
    return ExecutionRequest(
        request_id="image-request-1",
        asset_id="poster-1",
        work_id="no-lose-guard",
        media_type="image",
        provider="openai",
        prompt="A cinematic Afrobeats single cover at night",
        parameters=parameters,
    )


def approval() -> ExecutionApproval:
    return ExecutionApproval(
        asset_id="poster-1",
        media_type="image",
        provider="openai",
        approved_by="kelvin",
    )


def response(*images: bytes) -> Any:
    return SimpleNamespace(
        created=1777777777,
        data=[
            SimpleNamespace(b64_json=base64.b64encode(image).decode())
            for image in images
        ],
    )


def test_executes_approved_request_and_persists_outputs(tmp_path: Path) -> None:
    images = FakeImages(response=response(b"first-image", b"second-image"))
    adapter = OpenAIImageAdapter(
        FakeClient(images),
        model="gpt-image-2",
        output_dir=tmp_path,
    )
    execution = request(
        ExecutionParameter(name="size", value="1024x1024"),
        ExecutionParameter(name="quality", value="high"),
        ExecutionParameter(name="output_format", value="webp"),
        ExecutionParameter(name="n", value="2"),
    )

    receipt = ProviderExecutionService().execute(execution, approval(), adapter)

    assert images.received == {
        "model": "gpt-image-2",
        "prompt": execution.prompt,
        "size": "1024x1024",
        "quality": "high",
        "output_format": "webp",
        "n": 2,
    }
    assert receipt.external_id == "openai-image:1777777777"
    assert tuple(Path(item).read_bytes() for item in receipt.outputs) == (
        b"first-image",
        b"second-image",
    )
    assert all(Path(item).suffix == ".webp" for item in receipt.outputs)


@pytest.mark.parametrize(
    ("parameter", "message"),
    [
        (ExecutionParameter(name="style", value="cinematic"), "unsupported"),
        (ExecutionParameter(name="size", value="square"), "size"),
        (ExecutionParameter(name="quality", value="ultra"), "quality"),
        (ExecutionParameter(name="background", value="blue"), "background"),
        (ExecutionParameter(name="output_format", value="gif"), "output_format"),
        (ExecutionParameter(name="n", value="many"), "integer"),
        (ExecutionParameter(name="n", value="5"), "between 1 and 4"),
    ],
)
def test_rejects_unsupported_parameters_before_calling_provider(
    tmp_path: Path,
    parameter: ExecutionParameter,
    message: str,
) -> None:
    images = FakeImages(response=response(b"unused"))
    adapter = OpenAIImageAdapter(
        FakeClient(images),
        model="gpt-image-2",
        output_dir=tmp_path,
    )

    with pytest.raises(ValueError, match=message):
        ProviderExecutionService().execute(request(parameter), approval(), adapter)

    assert images.received is None


def test_rejects_empty_or_invalid_provider_outputs(tmp_path: Path) -> None:
    empty = OpenAIImageAdapter(
        FakeClient(FakeImages(response=SimpleNamespace(data=[]))),
        model="gpt-image-2",
        output_dir=tmp_path,
    )
    invalid = OpenAIImageAdapter(
        FakeClient(
            FakeImages(
                response=SimpleNamespace(
                    data=[SimpleNamespace(b64_json="not base64")],
                )
            )
        ),
        model="gpt-image-2",
        output_dir=tmp_path,
    )

    with pytest.raises(RuntimeError, match="no outputs"):
        ProviderExecutionService().execute(request(), approval(), empty)
    with pytest.raises(RuntimeError, match="invalid output"):
        ProviderExecutionService().execute(request(), approval(), invalid)


def test_factory_uses_secret_safe_configuration_and_default_model(tmp_path: Path) -> None:
    received: dict[str, Any] = {}

    def client_factory(**options: Any) -> FakeClient:
        received.update(options)
        return FakeClient(FakeImages(response=response(b"image")))

    configuration = ProviderConfiguration(
        provider="openai",
        credential_ref="OPENAI_API_KEY",
        media_types=("image",),
        timeout_seconds=45,
        options=(ProviderOption(name="output_dir", value=str(tmp_path)),),
    )
    adapter = ProviderConfigurationService().create_adapter(
        configuration,
        secret_source=SimpleNamespace(resolve=lambda reference: "secret-key"),
        factory=OpenAIImageAdapterFactory(client_factory),
    )

    assert adapter.provider == "openai"
    assert adapter.media_types == ("image",)
    assert received == {"api_key": "secret-key", "timeout": 45}
    assert "secret-key" not in repr(adapter)


def test_factory_passes_custom_model_and_endpoint(tmp_path: Path) -> None:
    received: dict[str, Any] = {}

    def client_factory(**options: Any) -> FakeClient:
        received.update(options)
        return FakeClient(FakeImages(response=response(b"image")))

    configuration = ProviderConfiguration(
        provider="openai",
        credential_ref="OPENAI_API_KEY",
        media_types=("image",),
        model="gpt-image-1.5",
        endpoint="https://api.example.test/v1",
        options=(ProviderOption(name="output_dir", value=str(tmp_path)),),
    )
    adapter = OpenAIImageAdapterFactory(client_factory).create(
        configuration,
        "secret-key",
    )

    ProviderExecutionService().execute(request(), approval(), adapter)

    assert received["base_url"] == "https://api.example.test/v1"
    assert adapter._client.images.received["model"] == "gpt-image-1.5"


def test_marks_only_declared_transient_failures_as_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import services.openai_image_adapter as module

    class TransientError(Exception):
        pass

    monkeypatch.setattr(module, "RateLimitError", TransientError)
    adapter = OpenAIImageAdapter(
        FakeClient(FakeImages(error=TransientError("secret provider detail"))),
        model="gpt-image-2",
        output_dir=tmp_path,
    )

    with pytest.raises(RetryableProviderError, match="temporarily failed") as captured:
        ProviderExecutionService().execute(request(), approval(), adapter)

    assert "secret provider detail" not in str(captured.value)
