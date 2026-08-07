from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from services.action_repository import ActionRepository

runner = CliRunner()


def make_campaign(tmp_path: Path) -> ActionRepository:
    campaign_root = (
        tmp_path / "organizations" / "kre" / "projects" / "campaign" / "campaigns" / "launch"
    )
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "kre" / "organization.yaml").write_text(
        "id: kre\nname: KRE\n", encoding="utf-8"
    )
    project_root = tmp_path / "organizations" / "kre" / "projects" / "campaign"
    (project_root / "project.yaml").write_text("id: campaign\nname: Campaign\n", encoding="utf-8")
    (campaign_root / "campaign.yaml").write_text("id: launch\nname: Launch\n", encoding="utf-8")
    return ActionRepository(tmp_path, "kre", "campaign", "launch")


def write_template(tmp_path: Path) -> None:
    template_root = tmp_path / "templates" / "execution"
    template_root.mkdir(parents=True)
    (template_root / "test-plan.yaml").write_text(
        """id: test-plan
name: Test Plan
variables:
  campaign_date:
    required: true
  channel:
    required: true
actions:
  - id: publish
    title: Publish to {{ channel }}
    due_date: "{{ campaign_date }}"
    channel: "{{ channel }}"
""",
        encoding="utf-8",
    )


def base_args(command: str) -> list[str]:
    return [
        "execution",
        "plan",
        command,
        "test-plan",
        "--org",
        "kre",
        "--project",
        "campaign",
        "--campaign",
        "launch",
    ]


def test_preview_accepts_repeated_template_variables(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    write_template(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            *base_args("preview"),
            "--var",
            "campaign_date=2026-09-01",
            "--var",
            "channel=instagram",
        ],
    )

    assert result.exit_code == 0
    assert "Publish to instagram" in result.stdout
    assert "2026-09-01" in result.stdout
    assert "instagram" in result.stdout
    assert repository.list() == ()


def test_apply_persists_rendered_template_variables(tmp_path: Path, monkeypatch) -> None:
    repository = make_campaign(tmp_path)
    write_template(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            *base_args("apply"),
            "--var",
            "campaign_date=2026-09-01",
            "--var",
            "channel=facebook",
        ],
    )

    assert result.exit_code == 0
    assert repository.load("publish").channel == "facebook"
    assert repository.load("publish").due_date.isoformat() == "2026-09-01"


def test_preview_rejects_malformed_template_variable(tmp_path: Path, monkeypatch) -> None:
    make_campaign(tmp_path)
    write_template(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, [*base_args("preview"), "--var", "channel"])

    assert result.exit_code == 1
    assert "key=value" in result.stdout


def test_preview_rejects_duplicate_template_variable(tmp_path: Path, monkeypatch) -> None:
    make_campaign(tmp_path)
    write_template(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            *base_args("preview"),
            "--var",
            "campaign_date=2026-09-01",
            "--var",
            "channel=instagram",
            "--var",
            "channel=facebook",
        ],
    )

    assert result.exit_code == 1
    assert "more than once" in result.stdout
