from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class WorkspaceSummary:
    """
    High-level summary of a CreativeOS workspace.

    This model is intentionally small.
    Additional fields will be introduced as the
    platform evolves.
    """

    project_name: str
    artist_name: str
    current_song: str
    upcoming_song: str
    active_campaigns: int
    workspace_path: Path
