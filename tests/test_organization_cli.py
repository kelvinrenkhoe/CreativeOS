from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from services.organization import OrganizationService

runner = CliRunner()


def _write_organization(root: Path, organization_id: str = "kre") -> None:
    organization_path = root / "organizations" / organization_id
    organization_path.mkdir(parents=True)
    (organization_path / "organization.yaml").write_text(
        "\n".join(
            (
                f"id: {organization_id}",
                "name: Kelvin Rankie Entertainment",
                "type: creator_business",
                "description: Production organization for CreativeOS.",
                "",
            )
        ),
        encoding="utf-8",
    )


def test_organization_service_discovers_repository_from_child(tmp_path: Path) -> None:
    _write_organization(tmp_path)
    child = tmp_path / "organizations" / "kre" / "projects"
    child.mkdir()

    service = OrganizationService.discover(child)

    assert service.repository_root == tmp_path.resolve()


def test_org_list_displays_organizations(tmp_path: Path, monkeypatch) -> None:
    _write_organization(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["org", "list"])

    assert result.exit_code == 0
    assert "kre" in result.output
    assert "Kelvin Rankie Entertainment" in result.output
    assert "creator_business" in result.output


def test_org_show_displays_one_organization(tmp_path: Path, monkeypatch) -> None:
    _write_organization(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["org", "show", "kre"])

    assert result.exit_code == 0
    assert "Kelvin Rankie Entertainment" in result.output
    assert "Production organization for CreativeOS." in result.output


def test_org_validate_reports_valid_organizations(tmp_path: Path, monkeypatch) -> None:
    _write_organization(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["org", "validate"])

    assert result.exit_code == 0
    assert "Valid:" in result.output
    assert "1 organization(s)" in result.output


def test_org_command_fails_outside_repository(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["org", "list"])

    assert result.exit_code == 1
    assert "organizations directory not found" in result.output


def test_org_show_rejects_path_traversal(tmp_path: Path, monkeypatch) -> None:
    _write_organization(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["org", "show", "../../secrets"])

    assert result.exit_code == 1
    assert "organization_id must contain only" in result.output
