from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from services.instagram_analytics_connector import (
    InstagramAnalyticsConfiguration,
    InstagramAnalyticsConnector,
    InstagramAnalyticsConnectorFactory,
    InstagramAnalyticsError,
    InstagramPublication,
)
from services.performance_ingestion import PerformanceRecord


@dataclass
class FakeTransport:
    responses: list[dict[str, Any]]
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def request(self, path: str, parameters: dict[str, str]) -> dict[str, Any]:
        self.calls.append((path, parameters))
        return self.responses.pop(0)


def connector(transport: FakeTransport) -> InstagramAnalyticsConnector:
    return InstagramAnalyticsConnector(
        transport,
        metrics=("reach", "views"),
        clock=lambda: datetime(2026, 7, 29, 8, 30, tzinfo=UTC),
    )


def test_ingests_aggregate_and_time_series_insights() -> None:
    transport = FakeTransport(
        responses=[
            {
                "data": [
                    {"name": "reach", "total_value": {"value": 1250}},
                    {
                        "name": "views",
                        "values": [
                            {"value": 1900, "end_time": "2026-07-29T08:00:00+0000"}
                        ],
                    },
                ]
            }
        ]
    )

    dataset = connector(transport).ingest(
        [InstagramPublication(asset_id="no-lose-guard-reel", media_id="media-456")]
    )

    assert transport.calls == [
        ("/media-456/insights", {"metric": "reach,views"}),
    ]
    assert dataset.records == (
        PerformanceRecord(
            asset_id="no-lose-guard-reel",
            platform="instagram",
            external_id="media-456",
            metric="views",
            value=1900.0,
            observed_at="2026-07-29T08:00:00Z",
        ),
        PerformanceRecord(
            asset_id="no-lose-guard-reel",
            platform="instagram",
            external_id="media-456",
            metric="reach",
            value=1250.0,
            observed_at="2026-07-29T08:30:00Z",
        ),
    )


def test_rejects_duplicate_publication_before_second_request() -> None:
    transport = FakeTransport(responses=[{"data": []}])
    publication = InstagramPublication(asset_id="asset-1", media_id="media-1")

    with pytest.raises(ValueError, match="duplicate Instagram publication"):
        connector(transport).ingest([publication, publication])

    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"data": ["invalid"]},
        {"data": [{"name": "reach", "values": []}]},
    ],
)
def test_rejects_invalid_provider_response(response: dict[str, Any]) -> None:
    transport = FakeTransport(responses=[response])

    with pytest.raises(InstagramAnalyticsError, match="invalid|no numeric"):
        connector(transport).ingest(
            [InstagramPublication(asset_id="asset-1", media_id="media-1")]
        )


def test_factory_resolves_secret_without_retaining_it() -> None:
    received: dict[str, Any] = {}

    def factory(credential: str, **options: Any) -> FakeTransport:
        received.update(credential=credential, **options)
        return FakeTransport(responses=[])

    configuration = InstagramAnalyticsConfiguration(
        credential_ref="INSTAGRAM_ACCESS_TOKEN",
        endpoint="https://graph.facebook.com/v24.0",
        metrics=("reach", "views"),
        timeout_seconds=45,
    )
    built = InstagramAnalyticsConnectorFactory(factory).create(
        configuration,
        SimpleNamespace(resolve=lambda _: "secret-token"),
    )

    assert received == {
        "credential": "secret-token",
        "endpoint": "https://graph.facebook.com/v24.0",
        "timeout": 45,
    }
    assert "secret-token" not in repr(built)


@pytest.mark.parametrize(
    "configuration",
    [
        InstagramAnalyticsConfiguration("TOKEN", "https://graph.facebook.com", ()),
        InstagramAnalyticsConfiguration("TOKEN", "https://graph.facebook.com", ("reach", "reach")),
        InstagramAnalyticsConfiguration("TOKEN", "https://graph.facebook.com", ("reach",), 0),
    ],
)
def test_rejects_invalid_configuration(
    configuration: InstagramAnalyticsConfiguration,
) -> None:
    with pytest.raises(ValueError):
        InstagramAnalyticsConnectorFactory().create(
            configuration,
            SimpleNamespace(resolve=lambda _: "secret-token"),
        )
