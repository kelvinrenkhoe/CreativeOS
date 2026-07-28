from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
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
from services.runway_video_adapter import RunwayVideoAdapter, RunwayVideoAdapterFactory


@dataclass
class FakeTransport:
    tasks: list[dict[str, Any]]
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    def request(self, method: str, path: str, payload: Any = None) -> dict[str, Any]:
        self.calls.append((method, path, payload))
        if method == "POST":
            return {"id": "task-123"}
        return self.tasks.pop(0)

    def download(self, url: str) -> bytes:
        self.calls.append(("DOWNLOAD", url, None))
        return b"video-bytes"


def request(*parameters: ExecutionParameter) -> ExecutionRequest:
    return ExecutionRequest(
        request_id="video-request-1",
        asset_id="teaser-1",
        work_id="no-lose-guard",
        media_type="video",
        provider="runway",
        prompt="A cinematic golden-hour London rooftop performance",
        parameters=parameters,
    )


def approval() -> ExecutionApproval:
    return ExecutionApproval(
        asset_id="teaser-1",
        media_type="video",
        provider="runway",
        approved_by="kelvin",
    )


def adapter(tmp_path: Path, transport: FakeTransport) -> RunwayVideoAdapter:
    return RunwayVideoAdapter(
        transport,
        model="gen4.5",
        output_dir=tmp_path,
        poll_interval=0,
        max_polls=3,
        sleeper=lambda _: None,
    )


def test_executes_text_video_and_persists_output(tmp_path: Path) -> None:
    transport = FakeTransport(
        tasks=[
            {"status": "RUNNING"},
            {"status": "SUCCEEDED", "output": ["https://example.test/video.mp4"]},
        ]
    )
    execution = request(
        ExecutionParameter(name="duration", value="8"),
        ExecutionParameter(name="ratio", value="720:1280"),
        ExecutionParameter(name="seed", value="42"),
    )

    receipt = ProviderExecutionService().execute(
        execution, approval(), adapter(tmp_path, transport)
    )

    assert transport.calls[0] == (
        "POST",
        "/v1/text_to_video",
        {
            "model": "gen4.5",
            "promptText": execution.prompt,
            "duration": 8,
            "ratio": "720:1280",
            "seed": 42,
        },
    )
    assert receipt.external_id == "runway-video:task-123"
    assert Path(receipt.outputs[0]).read_bytes() == b"video-bytes"


def test_uses_image_to_video_when_first_frame_is_supplied(tmp_path: Path) -> None:
    transport = FakeTransport(
        tasks=[{"status": "SUCCEEDED", "output": ["https://example.test/video.mp4"]}]
    )
    execution = request(
        ExecutionParameter(name="prompt_image", value="https://example.test/frame.png")
    )

    ProviderExecutionService().execute(
        execution, approval(), adapter(tmp_path, transport)
    )

    assert transport.calls[0][1] == "/v1/image_to_video"
    assert transport.calls[0][2]["promptImage"] == "https://example.test/frame.png"


@pytest.mark.parametrize(
    ("parameter", "message"),
    [
        (ExecutionParameter(name="style", value="cinematic"), "unsupported"),
        (ExecutionParameter(name="ratio", value="16:9"), "ratio"),
        (ExecutionParameter(name="duration", value="long"), "integer"),
        (ExecutionParameter(name="duration", value="11"), "between 2 and 10"),
        (ExecutionParameter(name="seed", value="-1"), "out of range"),
    ],
)
def test_rejects_invalid_parameters_before_provider_call(
    tmp_path: Path,
    parameter: ExecutionParameter,
    message: str,
) -> None:
    transport = FakeTransport(tasks=[])
    with pytest.raises(ValueError, match=message):
        ProviderExecutionService().execute(
            request(parameter), approval(), adapter(tmp_path, transport)
        )
    assert transport.calls == []


def test_maps_timeout_to_retryable_without_provider_detail(tmp_path: Path) -> None:
    transport = FakeTransport(tasks=[{"status": "RUNNING"}] * 3)
    with pytest.raises(RetryableProviderError, match="timed out") as captured:
        ProviderExecutionService().execute(
            request(), approval(), adapter(tmp_path, transport)
        )
    assert "task-123" not in str(captured.value)


def test_terminal_failure_stops_without_retry(tmp_path: Path) -> None:
    transport = FakeTransport(tasks=[{"status": "FAILED", "failure": "secret detail"}])
    with pytest.raises(RuntimeError, match="did not complete") as captured:
        ProviderExecutionService().execute(
            request(), approval(), adapter(tmp_path, transport)
        )
    assert "secret detail" not in str(captured.value)


def test_factory_uses_secret_safe_configuration(tmp_path: Path) -> None:
    received: dict[str, Any] = {}

    def factory(credential: str, **options: Any) -> FakeTransport:
        received.update(credential=credential, **options)
        return FakeTransport(
            tasks=[
                {"status": "SUCCEEDED", "output": ["https://example.test/video.mp4"]}
            ]
        )

    configuration = ProviderConfiguration(
        provider="runway",
        credential_ref="RUNWAYML_API_SECRET",
        media_types=("video",),
        timeout_seconds=45,
        options=(
            ProviderOption(name="output_dir", value=str(tmp_path)),
            ProviderOption(name="poll_interval", value="0"),
        ),
    )
    built = ProviderConfigurationService().create_adapter(
        configuration,
        secret_source=SimpleNamespace(resolve=lambda _: "secret-key"),
        factory=RunwayVideoAdapterFactory(factory),
    )

    assert received == {
        "credential": "secret-key",
        "endpoint": "https://api.dev.runwayml.com",
        "timeout": 45,
    }
    assert built.provider == "runway"
    assert "secret-key" not in repr(built)
