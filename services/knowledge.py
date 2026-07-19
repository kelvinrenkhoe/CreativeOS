"""Artist knowledge base loading service."""

from pathlib import Path

DEFAULT_DOCUMENTS = (
    "artist",
    "biography",
    "brand",
    "achievements",
    "audiences",
    "media-kit",
    "quotes",
)


class KnowledgeService:
    """Load reusable artist and song knowledge from Markdown files."""

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self._knowledge_dir = knowledge_dir or Path("knowledge")

    def load(self, document_name: str) -> str:
        path = self._knowledge_dir / f"{document_name}.md"
        return self._read(path)

    def load_song(self, song_slug: str) -> str:
        path = self._knowledge_dir / "songs" / f"{song_slug}.md"
        return self._read(path)

    def exists(self, document_name: str) -> bool:
        return (self._knowledge_dir / f"{document_name}.md").is_file()

    def song_exists(self, song_slug: str) -> bool:
        return (self._knowledge_dir / "songs" / f"{song_slug}.md").is_file()

    def build_context(self, song_slug: str | None = None) -> str:
        """Build a single AI context from all available knowledge."""
        sections: list[str] = []

        for document in DEFAULT_DOCUMENTS:
            if self.exists(document):
                sections.append(self.load(document))

        if song_slug and self.song_exists(song_slug):
            sections.append("# Song Knowledge\n\n" + self.load_song(song_slug))

        if not sections:
            return ""

        return "\n\n".join(sections)

    @staticmethod
    def _read(path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Knowledge document not found: {path}")

        return path.read_text(encoding="utf-8").strip()
