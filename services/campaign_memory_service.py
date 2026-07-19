"""Campaign memory persistence service."""

from pathlib import Path

from services.campaign_memory import CampaignMemory


class CampaignMemoryService:
    """Load and save campaign memory."""

    def __init__(self, memory_file: Path) -> None:
        self.memory_file = memory_file

    def load(self) -> CampaignMemory:
        """Load campaign memory from disk."""
        memory = CampaignMemory()

        if not self.memory_file.exists():
            return memory

        text = self.memory_file.read_text(encoding="utf-8").strip()

        if not text:
            return memory

        sections = text.split("\n\n---\n\n")

        for section in sections:
            lines = section.splitlines()

            if len(lines) < 4:
                continue

            purpose = lines[0].removeprefix("## ").strip()
            relative_path = lines[1].removeprefix("File: ").strip()
            content = "\n".join(lines[3:])

            memory.add(
                relative_path=relative_path,
                purpose=purpose,
                content=content,
            )

        return memory

    def save(self, memory: CampaignMemory) -> None:
        """Persist campaign memory."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        rendered = memory.render().replace("\n\n## ", "\n\n---\n\n## ")

        self.memory_file.write_text(rendered + "\n", encoding="utf-8")
