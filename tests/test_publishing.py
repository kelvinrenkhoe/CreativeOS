from dataclasses import dataclass, field

import pytest

from services.publishing import (
    PublicationApproval,
    PublicationReceipt,
    PublicationRequest,
    PublishingService,
)


@dataclass
class FakeAdapter:
    platform: str = "instagram"
    errors: tuple[str, ...] = ()
    published: list[PublicationRequest] = field(default_factory=list)

    def validate(self, request: PublicationRequest) -> tuple[str, ...]:
        return self.errors

    def publish(self, request: PublicationRequest) -> PublicationReceipt:
        self.published.append(request)
        return PublicationReceipt(
            platform=self.platform,
            external_id="post-123",
            url="https://example.test/post-123",
        )


def request() -> PublicationRequest:
    return PublicationRequest(
        asset_id="no-way-back-poster",
        platform=" Instagram ",
        content=" The journey begins. ",
        media=(" artwork/poster.png ",),
    )


def approval() -> PublicationApproval:
    return PublicationApproval(
        asset_id="no-way-back-poster",
        platform="instagram",
        approved_by="Kelvin",
    )


def test_publishes_validated_and_approved_request() -> None:
    adapter = FakeAdapter()

    receipt = PublishingService().publish(request(), approval(), adapter)

    assert receipt.external_id == "post-123"
    assert adapter.published == [
        PublicationRequest(
            asset_id="no-way-back-poster",
            platform="instagram",
            content="The journey begins.",
            media=("artwork/poster.png",),
        )
    ]


def test_rejects_approval_for_a_different_asset() -> None:
    wrong = PublicationApproval(
        asset_id="another-asset",
        platform="instagram",
        approved_by="Kelvin",
    )
    adapter = FakeAdapter()

    with pytest.raises(PermissionError, match="does not match"):
        PublishingService().publish(request(), wrong, adapter)

    assert adapter.published == []


def test_rejects_adapter_for_a_different_platform() -> None:
    adapter = FakeAdapter(platform="tiktok")

    with pytest.raises(ValueError, match="does not support"):
        PublishingService().publish(request(), approval(), adapter)

    assert adapter.published == []


def test_surfaces_adapter_validation_without_publishing() -> None:
    adapter = FakeAdapter(errors=("caption exceeds platform limit",))

    with pytest.raises(ValueError, match="caption exceeds platform limit"):
        PublishingService().publish(request(), approval(), adapter)

    assert adapter.published == []


@pytest.mark.parametrize("field", ["asset_id", "platform", "content"])
def test_rejects_empty_required_request_fields(field: str) -> None:
    values = {
        "asset_id": "no-way-back-poster",
        "platform": "instagram",
        "content": "The journey begins.",
    }
    values[field] = ""

    with pytest.raises(ValueError, match=field):
        PublishingService().publish(
            PublicationRequest(**values),
            approval(),
            FakeAdapter(),
        )


def test_rejects_invalid_receipt() -> None:
    class InvalidReceiptAdapter(FakeAdapter):
        def publish(self, request: PublicationRequest) -> PublicationReceipt:
            return PublicationReceipt(platform="instagram", external_id="")

    with pytest.raises(ValueError, match="external_id"):
        PublishingService().publish(request(), approval(), InvalidReceiptAdapter())
