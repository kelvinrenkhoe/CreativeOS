"""Typed configuration models for CreativeOS workspaces."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkspaceConfig:
    """Workspace identity settings."""

    name: str


@dataclass(frozen=True)
class ArtistConfig:
    """Creator profile settings."""

    name: str
    genre: str = ""
    country: str = ""


@dataclass(frozen=True)
class RepositoryConfig:
    """Repository paths relative to the workspace root."""

    songs: str = "songs"
    campaigns: str = "campaigns"
    books: str = "books"
    templates: str = "templates"
    assets: str = "assets"
    knowledge: str = "knowledge"
    media: str = "media"


@dataclass(frozen=True)
class AIConfig:
    """Optional AI provider settings."""

    provider: str = ""
    default_model: str = ""


@dataclass(frozen=True)
class CreativeOSConfig:
    """Complete CreativeOS workspace configuration."""

    version: int
    workspace: WorkspaceConfig
    artist: ArtistConfig
    repository: RepositoryConfig = field(default_factory=RepositoryConfig)
    ai: AIConfig = field(default_factory=AIConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreativeOSConfig":
        """Build and validate a configuration model from parsed YAML data."""
        version = data.get("version")
        if version != 1:
            raise ValueError("Unsupported configuration version. Expected version: 1.")

        workspace_data = data.get("workspace")
        artist_data = data.get("artist")
        if not isinstance(workspace_data, dict) or not workspace_data.get("name"):
            raise ValueError("workspace.name is required.")
        if not isinstance(artist_data, dict) or not artist_data.get("name"):
            raise ValueError("artist.name is required.")

        repository_data = data.get("repository", {})
        ai_data = data.get("ai", {})
        if not isinstance(repository_data, dict):
            raise ValueError("repository must be a mapping.")
        if not isinstance(ai_data, dict):
            raise ValueError("ai must be a mapping.")

        return cls(
            version=version,
            workspace=WorkspaceConfig(name=str(workspace_data["name"])),
            artist=ArtistConfig(
                name=str(artist_data["name"]),
                genre=str(artist_data.get("genre", "")),
                country=str(artist_data.get("country", "")),
            ),
            repository=RepositoryConfig(**repository_data),
            ai=AIConfig(**ai_data),
        )

    def repository_path(self, root: Path, key: str) -> Path:
        """Resolve a configured repository path against a workspace root."""
        try:
            relative_path = getattr(self.repository, key)
        except AttributeError as exc:
            raise KeyError(f"Unknown repository path: {key}") from exc
        return root / relative_path
