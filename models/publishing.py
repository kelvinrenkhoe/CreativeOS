"""Immutable models for deterministic campaign publishing plans."""

from dataclasses import dataclass
from enum import StrEnum


class PublishingError(ValueError):
    """Raised when a publishing plan is invalid."""


class PublishingPlatform(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"
    X = "x"


class PublishingFormat(StrEnum):
    REEL = "reel"
    SHORT = "short"
    FEED = "feed"
    STORY = "story"
    CANVAS = "canvas"
    POST = "post"


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class PublishingSlot:
    slot_id: str
    day: int
    time: str
    platform: PublishingPlatform
    content_format: PublishingFormat
    primary_asset_path: str
    supporting_asset_paths: tuple[str, ...] = ()
    dependency_slot_ids: tuple[str, ...] = ()
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.slot_id.strip():
            raise PublishingError("slot_id must not be empty")
        if self.day < 1 or self.day > 7:
            raise PublishingError("day must be between 1 and 7")
        parts = self.time.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise PublishingError("time must use HH:MM format")
        hour, minute = (int(part) for part in parts)
        if hour > 23 or minute > 59:
            raise PublishingError("time must use a valid 24-hour value")
        if not self.primary_asset_path.strip():
            raise PublishingError("primary_asset_path must not be empty")
        if len(self.supporting_asset_paths) != len(set(self.supporting_asset_paths)):
            raise PublishingError("supporting asset paths must be unique")
        if len(self.dependency_slot_ids) != len(set(self.dependency_slot_ids)):
            raise PublishingError("dependency slot ids must be unique")
        if self.slot_id in self.dependency_slot_ids:
            raise PublishingError("a slot cannot depend on itself")


@dataclass(frozen=True, slots=True)
class PublishingManifest:
    manifest_id: str
    campaign_id: str
    campaign_week: int
    timezone: str
    slots: tuple[PublishingSlot, ...]

    def __post_init__(self) -> None:
        if not self.manifest_id.strip() or not self.campaign_id.strip():
            raise PublishingError("manifest and campaign identifiers must not be empty")
        if self.campaign_week < 1:
            raise PublishingError("campaign_week must be positive")
        if not self.timezone.strip():
            raise PublishingError("timezone must not be empty")
        if not self.slots:
            raise PublishingError("slots must not be empty")
        slot_ids = tuple(slot.slot_id for slot in self.slots)
        if len(slot_ids) != len(set(slot_ids)):
            raise PublishingError("slot ids must be unique")
        expected = tuple(sorted(self.slots, key=lambda slot: (slot.day, slot.time, slot.slot_id)))
        if self.slots != expected:
            raise PublishingError("slots must be ordered by day, time, and slot id")
        known = set(slot_ids)
        for slot in self.slots:
            missing = set(slot.dependency_slot_ids) - known
            if missing:
                raise PublishingError("slot dependencies must reference manifest slots")
