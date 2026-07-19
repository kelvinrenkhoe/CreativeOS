from pathlib import Path

from services.campaign_memory import CampaignMemory
from services.campaign_memory_service import CampaignMemoryService


def test_load_missing_memory_returns_empty(tmp_path: Path) -> None:
    service = CampaignMemoryService(tmp_path / "memory.md")

    memory = service.load()

    assert memory.is_empty()


def test_save_and_reload_memory(tmp_path: Path) -> None:
    file = tmp_path / "memory.md"

    service = CampaignMemoryService(file)

    memory = CampaignMemory()

    memory.add(
        relative_path="captions/instagram.md",
        purpose="Instagram",
        content="Hello Instagram",
    )

    memory.add(
        relative_path="captions/facebook.md",
        purpose="Facebook",
        content="Hello Facebook",
    )

    service.save(memory)

    loaded = service.load()

    assert len(loaded.entries) == 2
    assert loaded.entries[0].content == "Hello Instagram"
    assert loaded.entries[1].content == "Hello Facebook"
