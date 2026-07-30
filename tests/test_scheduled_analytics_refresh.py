"""Tests for durable scheduled analytics refreshes."""

from datetime import UTC, datetime, timedelta

import pytest

from services.instagram_analytics_connector import InstagramPublication
from services.performance_ingestion import PerformanceDataset, PerformanceRecord
from services.scheduled_analytics_refresh import (
    AnalyticsRefreshSchedule,
    JsonAnalyticsRefreshStore,
    ScheduledAnalyticsRefreshError,
    ScheduledAnalyticsRefreshService,
)

STARTS_AT = datetime(2026, 7, 30, 8, tzinfo=UTC)
NOW = datetime(2026, 7, 30, 12, 30, tzinfo=UTC)


def schedule(
    *,
    schedule_id: str = "instagram-no-lose-guard",
    starts_at: datetime = STARTS_AT,
    interval: timedelta = timedelta(hours=1),
) -> AnalyticsRefreshSchedule:
    return AnalyticsRefreshSchedule(
        schedule_id=schedule_id,
        publications=(
            InstagramPublication(
                asset_id="no-lose-guard-reel-01",
                media_id="instagram-media-123",
            ),
        ),
        interval=interval,
        starts_at=starts_at,
    )


def dataset() -> PerformanceDataset:
    return PerformanceDataset(
        records=(
            PerformanceRecord(
                asset_id="no-lose-guard-reel-01",
                platform="instagram",
                external_id="instagram-media-123",
                metric="views",
                value=125.0,
                observed_at="2026-07-30T12:30:00Z",
            ),
        )
    )


class SuccessfulConnector:
    def __init__(self) -> None:
        self.calls = []

    def ingest(self, publications):
        self.calls.append(publications)
        return dataset()


class FailingConnector:
    def ingest(self, publications):
        raise RuntimeError("Instagram temporarily unavailable")


class InterruptedConnector:
    def ingest(self, publications):
        raise KeyboardInterrupt()


def test_due_window_returns_none_before_schedule_starts():
    service = ScheduledAnalyticsRefreshService()

    assert (
        service.due_window(
            schedule(),
            now=STARTS_AT - timedelta(seconds=1),
        )
        is None
    )


def test_due_window_returns_latest_window_after_downtime():
    service = ScheduledAnalyticsRefreshService()

    result = service.due_window(schedule(), now=NOW)

    assert result == datetime(2026, 7, 30, 12, tzinfo=UTC)


def test_ready_orders_schedules_by_window_then_schedule_id():
    service = ScheduledAnalyticsRefreshService()

    result = service.ready(
        (
            schedule(
                schedule_id="later",
                starts_at=STARTS_AT + timedelta(minutes=30),
            ),
            schedule(schedule_id="z-schedule"),
            schedule(schedule_id="a-schedule"),
        ),
        now=NOW,
    )

    assert tuple((item.schedule_id, window) for item, window in result) == (
        ("a-schedule", datetime(2026, 7, 30, 12, tzinfo=UTC)),
        ("z-schedule", datetime(2026, 7, 30, 12, tzinfo=UTC)),
        ("later", datetime(2026, 7, 30, 12, 30, tzinfo=UTC)),
    )


def test_refresh_collects_and_persists_successful_attempt(tmp_path):
    connector = SuccessfulConnector()
    store = JsonAnalyticsRefreshStore(tmp_path / "analytics-refresh.json")
    service = ScheduledAnalyticsRefreshService()
    configured = schedule()

    result = service.refresh(
        configured,
        connector,
        store,
        now=NOW,
    )

    assert result.replayed is False
    assert result.dataset == dataset()
    assert result.attempt is not None
    assert result.attempt.status == "completed"
    assert result.attempt.window_started_at == datetime(
        2026,
        7,
        30,
        12,
        tzinfo=UTC,
    )
    assert result.attempt.record_count == 1
    assert connector.calls == [configured.publications]
    assert store.load() == (result.attempt,)


def test_completed_window_is_not_collected_twice_after_restart(tmp_path):
    path = tmp_path / "analytics-refresh.json"
    connector = SuccessfulConnector()
    configured = schedule()

    first = ScheduledAnalyticsRefreshService().refresh(
        configured,
        connector,
        JsonAnalyticsRefreshStore(path),
        now=NOW,
    )
    replay = ScheduledAnalyticsRefreshService().refresh(
        configured,
        connector,
        JsonAnalyticsRefreshStore(path),
        now=NOW + timedelta(minutes=15),
    )

    assert first.attempt is not None
    assert first.attempt.status == "completed"
    assert replay.replayed is True
    assert replay.dataset is None
    assert replay.attempt == first.attempt
    assert len(connector.calls) == 1


def test_started_attempt_becomes_uncertain_after_restart(tmp_path):
    path = tmp_path / "analytics-refresh.json"
    configured = schedule()
    store = JsonAnalyticsRefreshStore(path)
    window = ScheduledAnalyticsRefreshService().due_window(
        configured,
        now=NOW,
    )
    assert window is not None

    started, acquired = store.begin(
        schedule_id=configured.schedule_id,
        window_started_at=window,
        now=NOW,
    )
    assert acquired is True
    assert started.status == "started"

    connector = SuccessfulConnector()
    result = ScheduledAnalyticsRefreshService().refresh(
        configured,
        connector,
        JsonAnalyticsRefreshStore(path),
        now=NOW,
    )

    assert result.replayed is True
    assert result.dataset is None
    assert result.attempt is not None
    assert result.attempt.status == "uncertain"
    assert connector.calls == []


def test_expected_connector_failure_is_recorded_without_retry(tmp_path):
    path = tmp_path / "analytics-refresh.json"
    configured = schedule()
    service = ScheduledAnalyticsRefreshService()

    result = service.refresh(
        configured,
        FailingConnector(),
        JsonAnalyticsRefreshStore(path),
        now=NOW,
    )
    replay = service.refresh(
        configured,
        SuccessfulConnector(),
        JsonAnalyticsRefreshStore(path),
        now=NOW,
    )

    assert result.attempt is not None
    assert result.attempt.status == "failed"
    assert result.attempt.failure_reason == ("RuntimeError: Instagram temporarily unavailable")
    assert result.dataset is None
    assert replay.replayed is True
    assert replay.attempt == result.attempt


def test_interruption_marks_attempt_uncertain(tmp_path):
    store = JsonAnalyticsRefreshStore(tmp_path / "analytics-refresh.json")

    with pytest.raises(KeyboardInterrupt):
        ScheduledAnalyticsRefreshService().refresh(
            schedule(),
            InterruptedConnector(),
            store,
            now=NOW,
        )

    attempts = store.load()
    assert len(attempts) == 1
    assert attempts[0].status == "uncertain"


@pytest.mark.parametrize(
    "configured",
    (
        schedule(interval=timedelta(0)),
        schedule(interval=timedelta(seconds=-1)),
        AnalyticsRefreshSchedule(
            schedule_id="empty",
            publications=(),
            interval=timedelta(hours=1),
            starts_at=STARTS_AT,
        ),
    ),
)
def test_invalid_schedules_are_rejected(configured):
    with pytest.raises(ScheduledAnalyticsRefreshError):
        ScheduledAnalyticsRefreshService().due_window(
            configured,
            now=NOW,
        )
