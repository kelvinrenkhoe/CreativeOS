from pathlib import Path

import pytest

from models.project_context import ProjectContext, ProjectContextError
from services.project_context import ProjectContextLoadError, ProjectContextService


def _write_organization(root: Path, organization_id: str = "kre") -> Path:
    organization_root = root / "organizations" / organization_id
    organization_root.mkdir(parents=True)
    (organization_root / "organization.yaml").write_text(
        f"id: {organization_id}\nname: Kelvin Rankie Entertainment\ntype: creator_business\n",
        encoding="utf-8",
    )
    return organization_root


def _write_project(
    organization_root: Path,
    project_id: str = "no-lose-guard",
    *,
    configured_id: str | None = None,
) -> Path:
    project_root = organization_root / "projects" / project_id
    project_root.mkdir(parents=True)
    (project_root / "project.yaml").write_text(
        "\n".join(
            (
                f"id: {configured_id or project_id}",
                "name: No Lose Guard",
                "type: music-release",
                "description: Release project",
                "",
            )
        ),
        encoding="utf-8",
    )
    return project_root


def test_project_context_normalizes_safe_identifiers() -> None:
    project = ProjectContext(
        project_id="No-Lose-Guard",
        name=" No Lose Guard ",
        project_type="Music Release",
    )

    assert project.project_id == "no-lose-guard"
    assert project.name == "No Lose Guard"
    assert project.project_type == "music-release"


def test_project_context_rejects_path_traversal() -> None:
    with pytest.raises(ProjectContextError):
        ProjectContext(project_id="../../secrets", name="Unsafe")


def test_project_service_lists_projects_for_one_organization(tmp_path: Path) -> None:
    kre_root = _write_organization(tmp_path, "kre")
    _write_project(kre_root)

    other_root = _write_organization(tmp_path, "grace-church")
    _write_project(other_root, "easter-conference")

    projects = ProjectContextService(tmp_path, "kre").list()

    assert [project.project_id for project in projects] == ["no-lose-guard"]


def test_project_service_loads_project_and_safe_path(tmp_path: Path) -> None:
    organization_root = _write_organization(tmp_path)
    project_root = _write_project(organization_root)
    service = ProjectContextService(tmp_path, "kre")

    project = service.load("no-lose-guard")

    assert project.name == "No Lose Guard"
    assert service.project_path("no-lose-guard") == project_root.resolve()


def test_project_service_rejects_directory_id_mismatch(tmp_path: Path) -> None:
    organization_root = _write_organization(tmp_path)
    _write_project(
        organization_root,
        "no-lose-guard",
        configured_id="different-project",
    )

    with pytest.raises(ProjectContextLoadError, match="does not match directory"):
        ProjectContextService(tmp_path, "kre").load("no-lose-guard")


def test_project_service_rejects_traversal_project_id(tmp_path: Path) -> None:
    _write_organization(tmp_path)
    service = ProjectContextService(tmp_path, "kre")

    with pytest.raises(ProjectContextLoadError):
        service.load("../../other-org")
