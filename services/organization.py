"""Organization discovery and loading for repository-native CreativeOS workspaces."""

from pathlib import Path

import yaml

from models.organization import Organization, OrganizationError

ORGANIZATIONS_DIRECTORY = "organizations"
ORGANIZATION_FILENAME = "organization.yaml"


class OrganizationLoadError(Exception):
    """Raised when organization configuration cannot be safely loaded."""


class OrganizationService:
    """Discover and load organizations beneath a CreativeOS repository root."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.organizations_root = self.repository_root / ORGANIZATIONS_DIRECTORY

    def list(self) -> tuple[Organization, ...]:
        """Return valid organizations in stable identifier order."""
        if not self.organizations_root.is_dir():
            return ()

        organizations: list[Organization] = []
        entries = self.organizations_root.iterdir()
        directories = sorted(path for path in entries if path.is_dir())
        for directory in directories:
            config_path = directory / ORGANIZATION_FILENAME
            if config_path.is_file():
                organizations.append(self._load_file(config_path, expected_id=directory.name))
        return tuple(organizations)

    def load(self, organization_id: str) -> Organization:
        """Load one organization by validated identifier."""
        try:
            requested = Organization(
                organization_id=organization_id,
                name="validation-placeholder",
            ).organization_id
        except OrganizationError as exc:
            raise OrganizationLoadError(str(exc)) from exc

        config_path = self.organizations_root / requested / ORGANIZATION_FILENAME
        if not config_path.is_file():
            raise OrganizationLoadError(f"unknown organization: {requested}")
        return self._load_file(config_path, expected_id=requested)

    def organization_path(self, organization_id: str) -> Path:
        """Return the safe directory for one existing organization."""
        organization = self.load(organization_id)
        path = (self.organizations_root / organization.organization_id).resolve()
        if path.parent != self.organizations_root.resolve():
            raise OrganizationLoadError("organization path escaped the organizations directory")
        return path

    def _load_file(self, config_path: Path, *, expected_id: str) -> Organization:
        try:
            with config_path.open("r", encoding="utf-8") as file:
                raw = yaml.safe_load(file)
        except OSError as exc:
            raise OrganizationLoadError(f"unable to read {config_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise OrganizationLoadError(f"invalid YAML in {config_path}: {exc}") from exc

        try:
            organization = Organization.from_dict(raw)
        except OrganizationError as exc:
            raise OrganizationLoadError(f"invalid organization configuration: {exc}") from exc

        if organization.organization_id != expected_id:
            raise OrganizationLoadError(
                "organization id "
                f"{organization.organization_id!r} does not match directory {expected_id!r}"
            )
        return organization
