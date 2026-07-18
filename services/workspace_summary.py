"""Workspace summary service for CreativeOS."""

from models.workspace_summary import WorkspaceSummary

from core.config import find_workspace
from core.project import Project


class WorkspaceSummaryService:
    """Builds a high-level summary of a CreativeOS workspace."""

    def __init__(self, project: Project) -> None:
        self.project = project

    def load(self) -> WorkspaceSummary:
        """Return a summary of the current CreativeOS workspace."""
        return WorkspaceSummary(
            project_name=self.project.name,
            artist_name=self.project.artist,
            current_song=self.project.current_song,
            upcoming_song=self.project.upcoming_song,
            active_campaigns=len(self.project.active_campaigns),
            workspace_path=find_workspace(),
        )
