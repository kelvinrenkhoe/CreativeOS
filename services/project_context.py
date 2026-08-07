"""Project discovery and loading beneath CreativeOS organizations."""

from pathlib import Path

import yaml

from models.project_context import ProjectContext, ProjectContextError
from services.organization import OrganizationService

PROJECTS_DIRECTORY = "projects"
PROJECT_FILENAME = "project.yaml"


class ProjectContextLoadError(Exception):
    """Raised when an organization project cannot be safely loaded."""


class ProjectContextService:
    """Discover and load projects scoped to one CreativeOS organization."""

    def __init__(self, repository_root: Path, organization_id: str) -> None:
        self.organization_service = OrganizationService(repository_root)
        self.organization = self.organization_service.load(organization_id)
        self.organization_root = self.organization_service.organization_path(organization_id)
        self.projects_root = self.organization_root / PROJECTS_DIRECTORY

    def list(self) -> tuple[ProjectContext, ...]:
        """Return valid projects in stable identifier order."""
        if not self.projects_root.is_dir():
            return ()

        projects: list[ProjectContext] = []
        entries = self.projects_root.iterdir()
        directories = sorted(path for path in entries if path.is_dir())
        for directory in directories:
            config_path = directory / PROJECT_FILENAME
            if config_path.is_file():
                projects.append(self._load_file(config_path, expected_id=directory.name))
        return tuple(projects)

    def load(self, project_id: str) -> ProjectContext:
        """Load one project by validated identifier."""
        try:
            requested = ProjectContext(
                project_id=project_id,
                name="validation-placeholder",
            ).project_id
        except ProjectContextError as exc:
            raise ProjectContextLoadError(str(exc)) from exc

        config_path = self.projects_root / requested / PROJECT_FILENAME
        if not config_path.is_file():
            organization_id = self.organization.organization_id
            raise ProjectContextLoadError(
                f"unknown project {requested!r} for organization {organization_id!r}"
            )
        return self._load_file(config_path, expected_id=requested)

    def project_path(self, project_id: str) -> Path:
        """Return the safe directory for one existing organization project."""
        project = self.load(project_id)
        path = (self.projects_root / project.project_id).resolve()
        if path.parent != self.projects_root.resolve():
            raise ProjectContextLoadError(
                "project path escaped the organization projects directory"
            )
        return path

    def _load_file(self, config_path: Path, *, expected_id: str) -> ProjectContext:
        try:
            with config_path.open("r", encoding="utf-8") as file:
                raw = yaml.safe_load(file)
        except OSError as exc:
            raise ProjectContextLoadError(f"unable to read {config_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ProjectContextLoadError(f"invalid YAML in {config_path}: {exc}") from exc

        try:
            project = ProjectContext.from_dict(raw)
        except ProjectContextError as exc:
            raise ProjectContextLoadError(f"invalid project configuration: {exc}") from exc

        if project.project_id != expected_id:
            raise ProjectContextLoadError(
                f"project id {project.project_id!r} does not match directory {expected_id!r}"
            )
        return project
