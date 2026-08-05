"""Tests for provider-backed creator-facing AI campaign planning."""

import json

from services.ai_campaign_planner import AICampaignPlanService


class StubProvider:
    name = "stub"
    model = "stub-model"

    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, str | None, float | None]] = []

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.calls.append((prompt, system_prompt, temperature))
        if self.error is not None:
            raise self.error
        return self.response


def valid_payload(campaign_name: str = "No Lose Guard") -> str:
    return json.dumps(
        {
            "campaign_name": campaign_name,
            "duration_days": 28,
            "objectives": ["Build awareness", "Grow saves"],
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


def test_provider_plan_parses_valid_structured_output() -> None:
    provider = StubProvider(valid_payload())

    plan = AICampaignPlanService(provider).plan("No Lose Guard")

    assert plan.campaign_name == "No Lose Guard"
    assert plan.duration_days == 28
    assert tuple(item.title for item in plan.objectives) == ("Build awareness", "Grow saves")
    assert plan.weeks[0].tasks[0].title == "Announcement"
    assert plan.errors == ()


def test_provider_prompt_requires_json_only_and_campaign_name() -> None:
    provider = StubProvider(valid_payload())

    AICampaignPlanService(provider).plan("No Lose Guard")

    prompt, system_prompt, temperature = provider.calls[0]
    assert '"No Lose Guard"' in prompt
    assert "Return one JSON object" in prompt
    assert "Do not include Markdown" in prompt
    assert system_prompt is not None and "Return valid JSON only" in system_prompt
    assert temperature == 0.4


def test_malformed_json_returns_plan_error() -> None:
    plan = AICampaignPlanService(StubProvider("not-json")).plan("No Lose Guard")

    assert plan.errors == ("Planner returned malformed JSON",)
    assert plan.weeks == ()


def test_non_object_json_returns_plan_error() -> None:
    plan = AICampaignPlanService(StubProvider("[]")).plan("No Lose Guard")

    assert plan.errors == ("Planner returned invalid structure",)


def test_missing_objectives_returns_plan_error() -> None:
    payload = json.loads(valid_payload())
    payload["objectives"] = []

    plan = AICampaignPlanService(StubProvider(json.dumps(payload))).plan("No Lose Guard")

    assert "objectives must be a non-empty array" in plan.errors[0]


def test_week_without_tasks_returns_plan_error() -> None:
    payload = json.loads(valid_payload())
    payload["weeks"][0]["tasks"] = []

    plan = AICampaignPlanService(StubProvider(json.dumps(payload))).plan("No Lose Guard")

    assert "week tasks must be a non-empty array" in plan.errors[0]


def test_invalid_duration_returns_plan_error() -> None:
    payload = json.loads(valid_payload())
    payload["duration_days"] = "28"

    plan = AICampaignPlanService(StubProvider(json.dumps(payload))).plan("No Lose Guard")

    assert "duration_days must be an integer" in plan.errors[0]


def test_provider_failure_returns_plan_error_without_raising() -> None:
    plan = AICampaignPlanService(
        StubProvider(error=TimeoutError("provider timed out"))
    ).plan("No Lose Guard")

    assert plan.errors == ("AI campaign planner failed: provider timed out",)


def test_different_provider_campaign_name_adds_warning() -> None:
    plan = AICampaignPlanService(StubProvider(valid_payload("Another Campaign"))).plan(
        "No Lose Guard"
    )

    assert plan.campaign_name == "Another Campaign"
    assert plan.warnings == ("Provider campaign name differed from the requested campaign",)


def test_without_provider_preserves_deterministic_fallback() -> None:
    plan = AICampaignPlanService().plan("No Lose Guard")

    assert plan.duration_days == 28
    assert len(plan.weeks) == 4
    assert plan.errors == ()
