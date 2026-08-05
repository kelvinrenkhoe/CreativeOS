"""Tests for the creator-facing AI campaign plan command."""

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_campaign_plan_renders_summary_objectives_and_weeks() -> None:
    result = runner.invoke(app, ["campaign", "plan", "No Lose Guard"])

    assert result.exit_code == 0
    assert "AI Campaign Plan: No Lose Guard" in result.stdout
    assert "28 days" in result.stdout
    assert "Increase release awareness" in result.stdout
    assert "Week 1" in result.stdout
    assert "Campaign announcement" in result.stdout
    assert "Week 4" in result.stdout
    assert "Thank-you post" in result.stdout


def test_campaign_plan_rejects_blank_name() -> None:
    result = runner.invoke(app, ["campaign", "plan", "   "])

    assert result.exit_code == 1
    assert "campaign_name must not be empty" in result.stdout
