"""CLI tests for durable weekly campaign content planning."""

from types import SimpleNamespace

from typer.testing import CliRunner

from cli.main import app
from cli.week_plan import CONTENT_PLANS_PATH

runner = CliRunner()


def test_week_plan_creates_and_then_loads_same_week(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.week_plan.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )

    arguments = [
        "campaign",
        "week",
        "plan",
        "no-lose-guard",
        "--week-start",
        "2026-08-03",
    ]
    first = runner.invoke(app, arguments)
    plan_path = tmp_path / CONTENT_PLANS_PATH / "no-lose-guard.json"
    before = plan_path.read_text(encoding="utf-8")
    second = runner.invoke(app, arguments)
    after = plan_path.read_text(encoding="utf-8")

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert before == after
    assert "Created:" in first.stdout
    assert "Loaded:" in second.stdout
    assert "2026-08-03" in first.stdout
    assert "2026-08-09" in first.stdout
    assert first.stdout.count("planned") == 7


def test_week_plan_requires_monday_start(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.week_plan.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )

    result = runner.invoke(
        app,
        [
            "campaign",
            "week",
            "plan",
            "no-lose-guard",
            "--week-start",
            "2026-08-04",
        ],
    )

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Monday" in result.stdout


def test_week_plan_fails_closed_for_corrupt_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.week_plan.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    plan_path = tmp_path / CONTENT_PLANS_PATH / "no-lose-guard.json"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("not-json\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "campaign",
            "week",
            "plan",
            "no-lose-guard",
            "--week-start",
            "2026-08-03",
        ],
    )

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "invalid weekly content plan snapshot" in result.stdout


def test_week_plan_replace_is_explicit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "cli.week_plan.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )
    arguments = [
        "campaign",
        "week",
        "plan",
        "no-lose-guard",
        "--week-start",
        "2026-08-03",
    ]

    assert runner.invoke(app, arguments).exit_code == 0
    replaced = runner.invoke(app, [*arguments, "--replace"])

    assert replaced.exit_code == 0
    assert "Created:" in replaced.stdout
    assert "week of 2026-08-03" in replaced.stdout
