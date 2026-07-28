from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from services.instagram_publishing_adapter import (
    InstagramPublishingAdapter,
    InstagramPublishingAdapterFactory,
    InstagramPublishingConfiguration,
    InstagramPublishingError,
)
from services.publishing import (
    PublicationApproval,
    PublicationRequest,
    PublishingService,
)


@dataclass
class FakeTransport:
    statuses: list[str] = field(default_factory=lambda: ["FINISHED"])
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append((method, path, payload))
        if path.endswith("/media"):
            return {"id": "container-123"}
        if path.endswith("/media_publish"):
            return {"id": "media-456"}
        return {"status_code": self.statuses.pop(0)}


def request(media: str = "https://cdn.example.test/reel.mp4") -> PublicationRequest:
    return PublicationRequest(
        asset_id="no-lose-guard-teaser",
        platform="instagram",
        content="No Lose Guard. September 1.",
        media=(media,),
    )


def approval() -> PublicationApproval:
    return PublicationApproval(
        asset_id="no-lose-guard-teaser",
        platform="instagram",
        approved_by="Kelvin",
    )


def adapter(transport: FakeTransport, *, max_polls: int = 3) -> InstagramPublishingAdapter:
    return InstagramPublishingAdapter(
        transport,
        account_id="17841400000000000",
        poll_interval=0,
        max_polls=max_polls,
        sleeper=lambda _: None,
    )


def test_publishes_approved_reel_after_processing() -> None:
    transport = FakeTransport(statuses=["IN_PROGRESS", "FINISHED"])

    receipt = PublishingService().publish(
        request(),
        approval(),
        adapter(transport),
    )

    assert transport.calls[0] == (
        "POST",
        "/17841400000000000/media",
        {
            "caption": "No Lose Guard. September 1.",
            "media_type": "REELS",
            "video_url": "https://cdn.example.test/reel.mp4",
        },
    )
    assert transport.calls[-1] == (
        "POST",
        "/17841400000000000/media_publish",
        {"creation_id": "container-123"},
    )
    assert receipt.external_id == "media-456"


def test_publishes_image_with_image_url() -> None:
    transport = FakeTransport()

    PublishingService().publish(
        request("https://cdn.example.test/poster.jpg"),
        approval(),
        adapter(transport),
    )

    assert transport.calls[0][2]["image_url"] == "https://cdn.example.test/poster.jpg"
    assert "media_type" not in transport.calls[0][2]


@pytest.mark.parametrize(
    ("invalid", "message"),
    [
        (
            PublicationRequest(
                asset_id="no-lose-guard-teaser",
                platform="instagram",
                content="caption",
                media=(),
            ),
            "exactly one",
        ),
        (request("file:///tmp/reel.mp4"), "public HTTPS"),
        (request("https://cdn.example.test/audio.mp3"), "not supported"),
        (
            PublicationRequest(
                asset_id="no-lose-guard-teaser",
                platform="instagram",
                content="caption",
                media=("https://cdn.example.test/poster.jpg",),
                scheduled_for="2026-09-01T12:00:00+01:00",
            ),
            "scheduled publishing",
        ),
    ],
)
def test_rejects_invalid_request_before_provider_call(
    invalid: PublicationRequest,
    message: str,
) -> None:
    transport = FakeTransport()

    with pytest.raises(ValueError, match=message):
        PublishingService().publish(invalid, approval(), adapter(transport))

    assert transport.calls == []


def test_processing_failure_stops_without_publishing() -> None:
    transport = FakeTransport(statuses=["ERROR"])

    with pytest.raises(InstagramPublishingError, match="processing failed"):
        PublishingService().publish(request(), approval(), adapter(transport))

    assert not any(path.endswith("/media_publish") for _, path, _ in transport.calls)


def test_timeout_requires_reconciliation_before_retry() -> None:
    transport = FakeTransport(statuses=["IN_PROGRESS"] * 2)

    with pytest.raises(InstagramPublishingError, match="reconcile before retrying"):
        PublishingService().publish(
            request(),
            approval(),
            adapter(transport, max_polls=2),
        )


def test_factory_resolves_secret_without_retaining_it() -> None:
    received: dict[str, Any] = {}

    def factory(credential: str, **options: Any) -> FakeTransport:
        received.update(credential=credential, **options)
        return FakeTransport()

    configuration = InstagramPublishingConfiguration(
        account_id="17841400000000000",
        credential_ref="INSTAGRAM_ACCESS_TOKEN",
        endpoint="https://graph.facebook.com/v24.0",
        timeout_seconds=45,
        poll_interval=0,
    )
    built = InstagramPublishingAdapterFactory(factory).create(
        configuration,
        SimpleNamespace(resolve=lambda _: "secret-token"),
    )

    assert received == {
        "credential": "secret-token",
        "endpoint": "https://graph.facebook.com/v24.0",
        "timeout": 45,
    }
    assert "secret-token" not in repr(built)
