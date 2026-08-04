"""Tests for the deterministic in-memory provider execution adapter."""

import pytest

from services.in_memory_provider import InMemoryProviderExecutionAdapter
from services.provider_execution import (
    ExecutionApproval,
    ExecutionParameter,
    ExecutionRequest,
    ProviderExecutionService,
)


def request(
    *,
    request_id: str = "request-1",
    prompt: str = "Create a cinematic release visual",
) -> ExecutionRequest:
    return ExecutionRequest(
        request_id=request_id,
        asset_id="asset-1",
        work_id="no-lose-guard",
        media_type="image",
        provider="in-memory",
        prompt=prompt,
        parameters=(ExecutionParameter(name="ratio", value="1:1"),),
    )


def approval() -> ExecutionApproval:
    return ExecutionApproval(
        asset_id="asset-1",
        media_type="image",
        provider="in-memory",
        approved_by="Kelvin",
    )


def test_adapter_implements_provider_contract() -> None:
    adapter = InMemoryProviderExecutionAdapter()

    assert adapter.provider == "in-memory"
    assert adapter.media_types == ("image", "video")
    assert adapter.receipts == ()


def test_provider_service_executes_request_and_returns_receipt() -> None:
    adapter = InMemoryProviderExecutionAdapter()

    receipt = ProviderExecutionService().execute(request(), approval(), adapter)

    assert receipt.request_id == "request-1"
    assert receipt.external_id.startswith("memory-")
    assert receipt.outputs == (f"memory://in-memory/image/{receipt.external_id}",)
    assert adapter.receipt("request-1") == receipt


def test_identical_request_replays_same_receipt() -> None:
    adapter = InMemoryProviderExecutionAdapter()
    service = ProviderExecutionService()

    first = service.execute(request(), approval(), adapter)
    second = service.execute(request(), approval(), adapter)

    assert second is first
    assert adapter.receipts == (first,)


def test_external_id_is_deterministic_across_adapter_instances() -> None:
    first = ProviderExecutionService().execute(
        request(),
        approval(),
        InMemoryProviderExecutionAdapter(),
    )
    second = ProviderExecutionService().execute(
        request(),
        approval(),
        InMemoryProviderExecutionAdapter(),
    )

    assert first.external_id == second.external_id
    assert first.outputs == second.outputs


def test_conflicting_request_id_is_rejected() -> None:
    adapter = InMemoryProviderExecutionAdapter()
    service = ProviderExecutionService()
    service.execute(request(), approval(), adapter)

    with pytest.raises(ValueError, match="different work"):
        service.execute(
            request(prompt="Create a different visual"),
            approval(),
            adapter,
        )


def test_validate_does_not_mutate_adapter_state() -> None:
    adapter = InMemoryProviderExecutionAdapter(provider="mock")

    errors = adapter.validate(request())

    assert errors == ("request provider is not supported",)
    assert adapter.receipts == ()


def test_receipts_are_returned_in_request_id_order() -> None:
    adapter = InMemoryProviderExecutionAdapter()
    service = ProviderExecutionService()

    second = service.execute(request(request_id="request-2"), approval(), adapter)
    first = service.execute(request(request_id="request-1"), approval(), adapter)

    assert adapter.receipts == (first, second)


def test_adapter_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="media_types must not be empty"):
        InMemoryProviderExecutionAdapter(media_types=())

    with pytest.raises(ValueError, match="media_types must be unique"):
        InMemoryProviderExecutionAdapter(media_types=("image", "IMAGE"))
