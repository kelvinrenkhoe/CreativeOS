"""Song management service for CreativeOS."""

import re
from pathlib import Path

from models.song import Song
from services.scaffold import ScaffoldService


class SongError(Exception):
    """Raised when a song operation cannot be completed."""


class SongService:
    """Handles song operations inside a CreativeOS workspace."""

    def __init__(self, scaffold_service: ScaffoldService | None = None) -> None:
        self.scaffold_service = scaffold_service or ScaffoldService()

    def create(self, name: str, workspace: Path) -> Song:
        """
        Create a new song workspace from the song scaffold.

        Args:
            name: Human-readable song name.
            workspace: Root directory of the CreativeOS workspace.

        Returns:
            The newly created Song.

        Raises:
            SongError: If the name is empty or the song already exists.
        """
        clean_name = name.strip()

        if not clean_name:
            raise SongError("Song name cannot be empty.")

        folder_name = self._slugify(clean_name)
        song_path = workspace.resolve() / "songs" / folder_name

        if song_path.exists():
            raise SongError(f"Song already exists: {clean_name}")

        self.scaffold_service.apply("song", song_path)

        return Song(name=clean_name, path=song_path)

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert a song name into a filesystem-friendly folder name."""
        slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip())
        return slug.strip("-")
