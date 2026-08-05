"""Tests for filesystem-backed campaign runtime locking."""

from datetime import UTC, datetime, timedelta

import pytest

from services.campaign_runtime_lock import (
    CampaignRuntimeLockedError,
    CampaignRuntimeLockOwnershipError,
    JsonCampaignRuntimeLockStore,
)

NOW = datetime(2026, 8, 5, 4, 0, tzinfo=UTC)


def test_acquire_and_release_campaign_lock(tmp_path) -> None:
    store = JsonCampaignRuntimeLockStore(tmp_path)

    lock = store.acquire("campaign-1", "owner-1", now=NOW)

    assert lock.owner_id == "owner-1"
    assert store.load("campaign-1") == lock
    store.release("campaign-1", "owner-1")
    assert not (tmp_path / "campaign-1.lock").exists()


def test_active_lock_rejects_another_owner(tmp_path) -> None:
    store = JsonCampaignRuntimeLockStore(tmp_path)
    store.acquire("campaign-1", "owner-1", now=NOW)

    with pytest.raises(CampaignRuntimeLockedError, match="owner-1"):
        store.acquire("campaign-1", "owner-2", now=NOW + timedelta(minutes=5))


def test_same_owner_acquire_is_idempotent(tmp_path) -> None:
    store = JsonCampaignRuntimeLockStore(tmp_path)
    first = store.acquire("campaign-1", "owner-1", now=NOW)

    second = store.acquire("campaign-1", "owner-1", now=NOW + timedelta(minutes=5))

    assert second == first


def test_stale_lock_is_recovered_by_new_owner(tmp_path) -> None:
    store = JsonCampaignRuntimeLockStore(tmp_path, stale_after=timedelta(minutes=10))
    store.acquire("campaign-1", "owner-1", now=NOW)

    lock = store.acquire("campaign-1", "owner-2", now=NOW + timedelta(minutes=11))

    assert lock.owner_id == "owner-2"


def test_release_rejects_non_owner(tmp_path) -> None:
    store = JsonCampaignRuntimeLockStore(tmp_path)
    store.acquire("campaign-1", "owner-1", now=NOW)

    with pytest.raises(CampaignRuntimeLockOwnershipError, match="owner-1"):
        store.release("campaign-1", "owner-2")


def test_release_missing_lock_is_safe(tmp_path) -> None:
    JsonCampaignRuntimeLockStore(tmp_path).release("campaign-1", "owner-1")
