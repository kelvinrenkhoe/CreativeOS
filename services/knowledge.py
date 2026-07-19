"""Artist knowledge base loading service."""

from pathlib import Path


class KnowledgeService:
    """Load reusable artist and song knowledge from Markdown files."""

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self._knowledge_dir = knowledge_dir or Path("knowledge")

    def load(self, document_name: str) -> str:
        """Load a top-level knowledge document by name."""
        path = self._knowledge_dir / f"{document_name}.md"
        return self._read(path)

    def load_song(self, song_slug: str) -> str:
        """Load song-specific knowledge by slug."""
        path = self._knowledge_dir / "songs" / f"{song_slug}.md"
        return self._read(path)

    def exists(self, document_name: str) -> bool:
        """Return whether a top-level knowledge document exists."""
        return (self._knowledge_dir / f"{document_name}.md").is_file()

    def song_exists(self, song_slug: str) -> bool:
        """Return whether a song-specific knowledge document exists."""
        return (self._knowledge_dir / "songs" / f"{song_slug}.md").is_file()

    @staticmethod
    def _read(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Knowledge document not found: {path}")

        return path.read_text(encoding="utf-8").strip()
