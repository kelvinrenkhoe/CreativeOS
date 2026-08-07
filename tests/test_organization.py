from pathlib import Path

import pytest

from models.organization import Organization, OrganizationError, OrganizationType
from services.organization import OrganizationLoadError, OrganizationService


def write_organization(root: Path, organization_id: str, content: str) -> None:
    directory = root / "organizations" / organization_id
    directory.mkdir(parents=True)
    (directory / "organization.yaml").write_text(content, encoding="utf-8")


def test_organization_normalizes_identity() -> None:
    organization = Organization(
        organization_id="kre",
        name="  Kelvin Rankie Entertainment  ",
        organization_type=OrganizationType.CREATOR_BUSINESS,
        description="  Production workspace  ",
    )

    assert organization.organization_id == "kre"
    assert organization.name == "Kelvin Rankie Entertainment"
    assert organization.description == "Production workspace"


def test_organization_rejects_path_like_identifier() -> None:
    with pytest.raises(OrganizationError):
        Organization(organization_id="../kre", name="KRE")


def test_service_loads_organization(tmp_path: Path) -> None:
    write_organization(
        tmp_path,
        "kre",
        "id: kre\nname: Kelvin Rankie Entertainment\ntype: creator_business\n",
    )

    organization = OrganizationService(tmp_path).load("kre")

    assert organization.organization_id == "kre"
    assert organization.organization_type is OrganizationType.CREATOR_BUSINESS


def test_service_lists_organizations_in_stable_order(tmp_path: Path) -> None:
    write_organization(tmp_path, "kre", "id: kre\nname: KRE\ntype: creator_business\n")
    write_organization(tmp_path, "agency-a", "id: agency-a\nname: Agency A\ntype: agency\n")

    organizations = OrganizationService(tmp_path).list()

    assert tuple(item.organization_id for item in organizations) == ("agency-a", "kre")


def test_service_rejects_directory_id_mismatch(tmp_path: Path) -> None:
    write_organization(tmp_path, "kre", "id: other\nname: KRE\ntype: creator_business\n")

    with pytest.raises(OrganizationLoadError, match="does not match directory"):
        OrganizationService(tmp_path).load("kre")


def test_service_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(OrganizationLoadError):
        OrganizationService(tmp_path).load("../../secrets")


def test_organization_path_stays_beneath_organizations_root(tmp_path: Path) -> None:
    write_organization(tmp_path, "kre", "id: kre\nname: KRE\ntype: creator_business\n")

    path = OrganizationService(tmp_path).organization_path("kre")

    assert path == (tmp_path / "organizations" / "kre").resolve()
