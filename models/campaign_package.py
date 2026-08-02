"""Immutable models for deterministic weekly campaign packages."""

from dataclasses import dataclass
from enum import StrEnum


class PackageError(ValueError):
    """Raised when a campaign package is invalid."""


class PackageMediaType(StrEnum):
    MARKDOWN = "text/markdown"
    JSON = "application/json"
    TEXT = "text/plain"


@dataclass(frozen=True, slots=True)
class PackageAsset:
    path: str
    media_type: PackageMediaType
    content: str

    def __post_init__(self) -> None:
        path = self.path.strip()
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise PackageError("path must be a safe relative path")
        if not isinstance(self.content, str) or not self.content.strip():
            raise PackageError("content must be a non-empty string")
        object.__setattr__(self, "path", path)


@dataclass(frozen=True, slots=True)
class PackageMetadata:
    creativeos_version: str
    schema_version: int
    campaign_id: str
    campaign_name: str
    campaign_week: int
    generated_at: str

    def __post_init__(self) -> None:
        for field_name in (
            "creativeos_version",
            "campaign_id",
            "campaign_name",
            "generated_at",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise PackageError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        if self.schema_version < 1:
            raise PackageError("schema_version must be positive")
        if self.campaign_week < 1:
            raise PackageError("campaign_week must be positive")


@dataclass(frozen=True, slots=True)
class PackageManifest:
    package_id: str
    campaign_id: str
    campaign_week: int
    asset_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.package_id.strip() or not self.campaign_id.strip():
            raise PackageError("package and campaign identifiers must not be empty")
        if self.campaign_week < 1:
            raise PackageError("campaign_week must be positive")
        if not self.asset_paths:
            raise PackageError("asset_paths must not be empty")
        if tuple(sorted(self.asset_paths)) != self.asset_paths:
            raise PackageError("asset_paths must be sorted")
        if len(self.asset_paths) != len(set(self.asset_paths)):
            raise PackageError("asset_paths must be unique")


@dataclass(frozen=True, slots=True)
class CampaignPackage:
    package_id: str
    root_path: str
    metadata: PackageMetadata
    manifest: PackageManifest
    assets: tuple[PackageAsset, ...]

    def __post_init__(self) -> None:
        paths = tuple(asset.path for asset in self.assets)
        if tuple(sorted(paths)) != paths:
            raise PackageError("assets must be sorted by path")
        if len(paths) != len(set(paths)):
            raise PackageError("asset paths must be unique")
        if paths != self.manifest.asset_paths:
            raise PackageError("manifest asset paths must match package assets")

    def get(self, path: str) -> PackageAsset:
        for asset in self.assets:
            if asset.path == path:
                return asset
        raise PackageError(f"package asset not found: {path}")
