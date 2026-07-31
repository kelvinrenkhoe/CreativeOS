"""Tests for durable campaign runtime audit history."""

import json
from datetime import UTC, datetime

import pytest

from services.audit_history_store import (
    AuditHistoryStateError,
    JsonAuditHistoryStore,
)
from services.operations_dashboard import AuditEvent, AuditHistory

NOW = datetime(2026, 7, 31, 8, tzinfo=UTC)


def history() -> AuditHistory:
    return AuditHistory(
        events=(
            AuditEvent(
                event_id="request-01:completed",
                occurred_at=NOW,
                category="execution",
                action="completed",
                subject_id="request-01",
                actor="creativeos-cli",
                reference_id="provider-asset-01",
                detail="attempt=1",
            ),
        )
    )


def test_audit_history_round_trips_atomically(tmp_path) -> None:
    path = tmp_path / "audit-history.json"
    store = JsonAuditHistoryStore(path)

    store.save(history())

    assert store.load() == history()
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1


def test_missing_audit_history_loads_empty_without_creating_file(tmp_path) -> None:
    path = tmp_path / "audit-history.json"

    assert JsonAuditHistoryStore(path).load() == AuditHistory()
    assert not path.exists()


def test_rejects_incompatible_audit_history(tmp_path) -> None:
    path = tmp_path / "audit-history.json"
    path.write_text('{"version": 999, "events": []}\n', encoding="utf-8")

    with pytest.raises(AuditHistoryStateError, match="unsupported"):
        JsonAuditHistoryStore(path).load()
