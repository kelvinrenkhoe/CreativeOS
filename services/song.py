from pathlib import Path

from models.song import Song


class SongService:
    """Handles song operations inside a CreativeOS workspace."""

    def create(self, name: str, workspace: Path) -> Song:
        """
        Create a new song workspace.

        Args:
            name: Human-readable song name.
            workspace: Root path of the CreativeOS workspace.

        Returns:
            Song: The created song model.

        Raises:
            NotImplementedError: Until the creation workflow is implemented.
        """
        raise NotImplementedError