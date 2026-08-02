"""Immutable models for deterministic press and media packages."""

from dataclasses import dataclass
from enum import StrEnum

from models.media import MediaChannel, MediaContext, MediaError, MediaGoal


class PressAssetType(StrEnum):
    PRESS_RELEASE = "press_release"
    BLOG_ARTICLE = "blog_article"
    PLAYLIST_PITCH = "playlist_pitch"
    INTERVIEW_PITCH = "interview_pitch"
    ARTIST_BIOGRAPHY = "artist_biography"
    SONG_STORY = "song_story"
    MEDIA_KIT_SUMMARY = "media_kit_summary"
    QUOTE_SHEET = "quote_sheet"
    PRESS_HEADLINE = "press_headline"
    SOCIAL_PRESS_SNIPPET = "social_press_snippet"


@dataclass(frozen=True, slots=True)
class PressAsset:
    asset_id: str
    asset_type: PressAssetType
    channel: MediaChannel
    goal: MediaGoal
    title: str
    body: str

    def __post_init__(self) -> None:
        for field_name in ("asset_id", "title", "body"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise MediaError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())


@dataclass(frozen=True, slots=True)
class PressPackage:
    package_id: str
    context: MediaContext
    assets: tuple[PressAsset, ...]

    def __post_init__(self) -> None:
        if not self.assets:
            raise MediaError("assets must not be empty")
        asset_types = tuple(asset.asset_type for asset in self.assets)
        if len(asset_types) != len(set(asset_types)):
            raise MediaError("asset types must be unique")

    def render(self) -> str:
        lines = [
            f"# Media Package: {self.context.campaign_name}",
            "",
            f"Artist: {self.context.artist}",
            f"Campaign week: {self.context.campaign_week}",
            f"Audience: {self.context.audience}",
            f"CTA: {self.context.call_to_action}",
        ]
        for asset in self.assets:
            lines.extend(("", f"## {asset.title}", asset.body))
        return "\n".join(lines)
