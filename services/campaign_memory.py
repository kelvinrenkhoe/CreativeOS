"""Campaign memory models for coordinated asset generation."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CampaignMemoryEntry:
    """A previously generated campaign asset."""

    relative_path: str
    purpose: str
    content: str


@dataclass(slots=True)
class CampaignMemory:
    """Ordered memory of campaign assets generated during a run."""

    entries: list[CampaignMemoryEntry] = field(default_factory=list)

    def add(
        self,
        *,
        relative_path: str,
        purpose: str,
        content: str,
    ) -> None:
        """Add a generated campaign asset to memory."""
        self.entries.append(
            CampaignMemoryEntry(
                relative_path=relative_path,
                purpose=purpose,
                content=content.strip(),
            )
        )

    def is_empty(self) -> bool:
        """Return whether no campaign assets have been recorded."""
        return not self.entries

    def render(self) -> str:
        """Render campaign memory as reusable prompt context."""
        if self.is_empty():
            return "No campaign assets have been generated yet."

        sections = []

        for entry in self.entries:
            sections.append(
                "\n".join(
                    (
                        f"## {entry.purpose}",
                        f"File: {entry.relative_path}",
                        "",
                        entry.content,
                    )
                )
            )

        return "\n\n".join(sections)
