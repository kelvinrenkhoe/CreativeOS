from dataclasses import dataclass, field

import pytest

from services.provider_execution import (
    ExecutionApproval,
    ExecutionParameter,
    ExecutionReceipt,
    ExecutionRequest,
    ProviderExecutionService,
)


@dataclass
class FakeAdapter:
    provider: str = "open-video"
    media_types: tuple[str, ...] = ("video",)
    errors: tuple[str, ...] = ()
    executed: list[ExecutionRequest] = field(default_factory=list)

    def validate(self, request: ExecutionRequest) -> tuple[str, ...]:
        return self.errors

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        self.executed.append(request)
        return ExecutionReceipt(
            request_id=request.request_id,
            asset_id=request.asset_id,
            media_type=request.media_type,
            provider=request.provider,
            external_id="generation-123",
            outputs=("provider://generation-123/video.mp4",),
        )


def request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id=" departure-shot-01 ",
        asset_id=" no-way-back-video-01 ",
        work_id=" no-way-back ",
        media_type=" Video ",
        provider=" Open-Video ",
        prompt=" A cinematic departure scene. ",
        parameters=(
            ExecutionParameter(name=" Aspect-Ratio ", value=" 16:9 "),
            ExecutionParameter(name=" Duration ", value=" 5 "),
        ),
    )


def approval() -> ExecutionApproval:
    return ExecutionApproval(
        asset_id="no-way-back-video-01",
        media_type="video",
        provider="open-video",
        approved_by="Kelvin",
    )


def test_executes_validated_and_approved_request() -> None:
    adapter = FakeAdapter()

    receipt = ProviderExecutionService().execute(request(), approval(), adapter)

    assert receipt.external_id == "generation-123"
    assert adapter.executed == [
        ExecutionRequest(
            request_id="departure-shot-01",
            asset_id="no-way-back-video-01",
            work_id="no-way-back",
            media_type="video",
            provider="open-video",
            prompt="A cinematic departure scene.",
            parameters=(
                ExecutionParameter(name="aspect-ratio", value="16:9"),
                ExecutionParameter(name="duration", value="5"),
            ),
        )
    ]


def test_rejects_approval_for_a_different_provider() -> None:
    wrong = ExecutionApproval(
        asset_id="no-way-back-video-01",
        media_type="video",
        provider="another-provider",
        approved_by="Kelvin",
    )
    adapter = FakeAdapter()

    with pytest.raises(PermissionError, match="does not match"):
        ProviderExecutionService().execute(request(), wrong, adapter)

    assert adapter.executed == []


@pytest.mark.parametrize(
    ("adapter", "message"),
    [
        (FakeAdapter(provider="another-provider"), "provider"),
        (FakeAdapter(media_types=("image",)), "media_type"),
    ],
)
def test_rejects_unsupported_adapter_capability(
    adapter: FakeAdapter,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ProviderExecutionService().execute(request(), approval(), adapter)

    assert adapter.executed == []


def test_surfaces_adapter_validation_without_executing() -> None:
    adapter = FakeAdapter(errors=("duration exceeds provider limit",))

    with pytest.raises(ValueError, match="duration exceeds provider limit"):
        ProviderExecutionService().execute(request(), approval(), adapter)

    assert adapter.executed == []


@pytest.mark.parametrize("media_type", ["", "audio"])
def test_rejects_invalid_media_type(media_type: str) -> None:
    invalid = ExecutionRequest(
        request_id="request-1",
        asset_id="asset-1",
        work_id="work-1",
        media_type=media_type,
        provider="open-video",
        prompt="Prompt",
    )

    with pytest.raises(ValueError, match="media_type"):
        ProviderExecutionService().execute(invalid, approval(), FakeAdapter())


def test_rejects_duplicate_parameter_names() -> None:
    duplicate = ExecutionRequest(
        request_id="request-1",
        asset_id="asset-1",
        work_id="work-1",
        media_type="video",
        provider="open-video",
        prompt="Prompt",
        parameters=(
            ExecutionParameter(name="duration", value="5"),
            ExecutionParameter(name=" Duration ", value="10"),
        ),
    )

    with pytest.raises(ValueError, match="unique"):
        ProviderExecutionService().execute(duplicate, approval(), FakeAdapter())


def test_rejects_receipt_for_a_different_request() -> None:
    class InvalidReceiptAdapter(FakeAdapter):
        def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
            return ExecutionReceipt(
                request_id="another-request",
                asset_id=request.asset_id,
                media_type=request.media_type,
                provider=request.provider,
                external_id="generation-123",
            )

    with pytest.raises(ValueError, match="receipt does not match"):
        ProviderExecutionService().execute(request(), approval(), InvalidReceiptAdapter())
