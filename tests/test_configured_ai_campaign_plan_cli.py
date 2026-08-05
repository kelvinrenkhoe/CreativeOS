"""Tests for configured-provider AI campaign planning."""

import json
from types import SimpleNamespace

from typer.testing import CliRunner

import cli.campaign_plan as campaign_plan_cli
from cli.main import app

runner = CliRunner()


class StubProvider:
    name = "stub"
    model = "stub-model"

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.calls += 1
        return self.response


def payload(campaign_name: str = "No Lose Guard") -> str:
    return json.dumps(
        {
            "campaign_name": campaign_name,
            "duration_days": 28,
            "objectives": ["Build awareness"],
            "weeks": [
                {
                    "number": 1,
                    "objective": "Introduce the story",
                    "tasks": [
                        {
                            "title": "Announcement",
                            "description": "Introduce the campaign narrative.",
                        }
                    ],
                }
            ],
        }
    )


def install_provider(monkeypatch, provider: StubProvider) -> None:
    project = SimpleNamespace(config=SimpleNamespace(ai=object()))
    monkeypatch.setattr(campaign_plan_cli.Project, "discover", lambda: project)

    class StubManager:
        def __init__(self, config: object) -> None:
            self.config = config

        def default(self) -> StubProvider:
            return provider

    monkeypatch.setattr(campaign_plan_cli, "AIManager", StubManager)


def test_ai_plan_uses_configured_provider_by_default(monkeypatch) -> None:
    provider = StubProvider(payload())
    install_provider(monkeypatch, provider)

    result = runner.invoke(
        app,
        ["campaign", "ai-plan", "No Lose Guard"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    assert provider.calls == 1
    assert "stub" in result.stdout
    assert "Build awareness" in result.stdout


def test_ai_plan_deterministic_flag_skips_workspace_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        campaign_plan_cli.Project,
        "discover",
        lambda: (_ for _ in ()).throw(AssertionError("workspace should not be loaded")),
    )

    result = runner.invoke(
        app,
        ["campaign", "ai-plan", "No Lose Guard", "--deterministic"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    assert "deterministic" in result.stdout


def test_ai_plan_renders_provider_warnings(monkeypatch) -> None:
    install_provider(monkeypatch, StubProvider(payload("Different Campaign")))

    result = runner.invoke(
        app,
        ["campaign", "ai-plan", "No Lose Guard"],
        terminal_width=180,
    )

    assert result.exit_code == 0
    assert "Warnings" in result.stdout
    assert "Provider campaign name differed" in result.stdout


def test_ai_plan_renders_provider_errors_and_exits_one(monkeypatch) -> None:
    install_provider(monkeypatch, StubProvider("not-json"))

    result = runner.invoke(app, ["campaign", "ai-plan", "No Lose Guard"])

    assert result.exit_code == 1
    assert "Planner returned malformed JSON" in result.stdout
    assert "AI Campaign Plan" not in result.stdout
