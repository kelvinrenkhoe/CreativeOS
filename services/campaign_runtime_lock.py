"""Filesystem-backed campaign runtime locking with stale-lock recovery."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

DEFAULT_STALE_AFTER = timedelta(minutes=30)


class CampaignRuntimeLockError(RuntimeError):
    """Base error for campaign runtime locking."""


class CampaignRuntimeLockedError(CampaignRuntimeLockError):
    """Raised when another owner holds a non-stale campaign lock."""


class CampaignRuntimeLockOwnershipError(CampaignRuntimeLockError):
    """Raised when a caller attempts to release another owner's lock."""


@dataclass(frozen=True, slots=True)
class CampaignRuntimeLock:
    """Persisted campaign lock metadata."""

    campaign_id: str
    owner_id: str
    acquired_at: datetime


class JsonCampaignRuntimeLockStore:
    """Acquire and release campaign-scoped locks using atomic directory creation."""

    def __init__(
        self,
        directory: Path,
        *,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> None:
        if stale_after <= timedelta(0):
            raise ValueError("stale_after must be positive")
        self.directory = directory
        self.stale_after = stale_after

    def acquire(
        self,
        campaign_id: str,
        owner_id: str,
        *,
        now: datetime | None = None,
    ) -> CampaignRuntimeLock:
        """Acquire a campaign lock, replacing it only when it is stale."""
        reference_time = now or datetime.now(UTC)
        lock_path = self._lock_path(campaign_id)
        self.directory.mkdir(parents=True, exist_ok=True)

        try:
            lock_path.mkdir()
        except FileExistsError:
            current = self.load(campaign_id)
            if current.owner_id == owner_id:
                return current
            if reference_time - current.acquired_at <= self.stale_after:
                raise CampaignRuntimeLockedError(
                    f"campaign {campaign_id} is locked by {current.owner_id}"
                ) from None
            shutil.rmtree(lock_path)
            lock_path.mkdir()

        lock = CampaignRuntimeLock(campaign_id, owner_id, reference_time)
        self._metadata_path(lock_path).write_text(
            json.dumps(
                {
                    "campaign_id": campaign_id,
                    "owner_id": owner_id,
                    "acquired_at": reference_time.isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return lock

    def release(self, campaign_id: str, owner_id: str) -> None:
        """Release a lock only when the supplied owner holds it."""
        lock_path = self._lock_path(campaign_id)
        if not lock_path.exists():
            return
        current = self.load(campaign_id)
        if current.owner_id != owner_id:
            raise CampaignRuntimeLockOwnershipError(
                f"campaign {campaign_id} lock is owned by {current.owner_id}"
            )
        shutil.rmtree(lock_path)

    def load(self, campaign_id: str) -> CampaignRuntimeLock:
        """Load one persisted lock."""
        path = self._metadata_path(self._lock_path(campaign_id))
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            acquired_at = datetime.fromisoformat(payload["acquired_at"])
            if acquired_at.tzinfo is None:
                acquired_at = acquired_at.replace(tzinfo=UTC)
            return CampaignRuntimeLock(
                campaign_id=str(payload["campaign_id"]),
                owner_id=str(payload["owner_id"]),
                acquired_at=acquired_at,
            )
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CampaignRuntimeLockError(
                f"campaign {campaign_id} lock metadata is corrupt"
            ) from exc

    def _lock_path(self, campaign_id: str) -> Path:
        unsafe = (
            not campaign_id
            or campaign_id in {".", ".."}
            or "/" in campaign_id
            or "\\" in campaign_id
        )
        if unsafe:
            raise ValueError("campaign_id must be a safe filename component")
        return self.directory / f"{campaign_id}.lock"

    @staticmethod
    def _metadata_path(lock_path: Path) -> Path:
        return lock_path / "lock.json"
