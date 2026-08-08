from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from services.campaign_start import CampaignStartError, CampaignStartService

runner = CliRunner()


def make_workspace(tmp_path: Path) -> None:
    project_root = tmp_path / "organizations" / "acme" / "projects" / "product-x"
    project_root.mkdir(parents=True)
    (tmp_path / "organizations" / "acme" / "organization.yaml").write_text(
        "id: acme\nname: Acme\n",
        encoding="utf-8",
    )
    (project_root / "project.yaml").write_text(
        "id: product-x\nname: Product X\ntype: product\n",
        encoding="utf-8",
    )
    templates_root = tmp_path / "templates" / "execution"
    templates_root.mkdir(parents=True)
    (templates_root / "product-campaign.yaml").write_text(
        "id: product-campaign\nname: Product Campaign\nactions: []\n",
        encoding="utf-8",
    )
    packs_root = tmp_path / "templates" / "domain-packs"
    packs_root.mkdir(parents=True)
    (packs_root / "product-launch.yaml").write_text(
        "id: product-launch\n"
        "name: Product Launch\n"
        "templates:\n"
        "  - product-campaign\n"
        "default_template: product-campaign\n"
        "planning:\n"
        "  anchor: launch_date\n"
        "  start_offset_days: -30\n"
        "  end_offset_days: 14\n"
        "  milestones:\n"
        "    campaign_start: -30\n"
        "    launch: 0\n"
        "    review: 14\n",
        encoding="utf-8",
    )


def test_campaign_start_plan_exposes_domain_anchor_name(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    service = CampaignStartService(tmp_path, "acme", "product-x")

    plan = service.plan(
        "launch",
        "Product X Launch",
        date(2026, 11, 10),
        objective="Launch Product X.",
        channels=("linkedin",),
        domain_pack_id="product-launch",
    )

    assert plan.anchor_name == "launch_date"
    assert plan.anchor_date == date(2026, 11, 10)
    assert plan.campaign.start_date == date(2026, 10, 11)
    assert plan.campaign.end_date == date(2026, 11, 24)


def test_campaign_start_preserves_release_date_keyword_alias(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    service = CampaignStartService(tmp_path, "acme", "product-x")

    plan = service.plan(
        "launch",
        "Product X Launch",
        objective="Launch Product X.",
        channels=("linkedin",),
        domain_pack_id="product-launch",
        release_date=date(2026, 11, 10),
    )

    assert plan.release_date == plan.anchor_date


def test_campaign_start_rejects_two_anchor_inputs(tmp_path: Path) -> None:
    make_workspace(tmp_path)
    service = CampaignStartService(tmp_path, "acme", "product-x")

    try:
        service.plan(
            "launch",
            "Product X Launch",
            date(2026, 11, 10),
            objective="Launch Product X.",
            channels=("linkedin",),
            domain_pack_id="product-launch",
            release_date=date(2026, 11, 10),
        )
    except CampaignStartError as exc:
        assert "not both" in str(exc)
    else:
        raise AssertionError("expected CampaignStartError")


def test_campaign_start_cli_accepts_generic_anchor(tmp_path: Path, monkeypatch) -> None:
    make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "campaign",
            "start",
            "launch",
            "--name",
            "Product X Launch",
            "--org",
            "acme",
            "--project",
            "product-x",
            "--domain-pack",
            "product-launch",
            "--anchor",
            "2026-11-10",
            "--channel",
            "linkedin",
        ],
    )

    assert result.exit_code == 0
    assert "launch_date" in result.stdout
    assert "2026-11-10" in result.stdout
    assert "product-launch" in result.stdout


def test_campaign_start_cli_rejects_anchor_and_release_together(
    tmp_path: Path,
    monkeypatch,
) -> None:
    make_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "campaign",
            "start",
            "launch",
            "--name",
            "Product X Launch",
            "--org",
            "acme",
            "--project",
            "product-x",
            "--domain-pack",
            "product-launch",
            "--anchor",
            "2026-11-10",
            "--release",
            "2026-11-10",
            "--channel",
            "linkedin",
        ],
    )

    assert result.exit_code == 1
    assert "provide --anchor or --release, not both" in result.stdout
