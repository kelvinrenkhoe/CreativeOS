from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Song:
    """
    Represents a song inside a CreativeOS workspace.
    """

    name: str
    path: Path