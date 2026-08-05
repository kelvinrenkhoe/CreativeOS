"""Tests for deterministic creator-facing AI campaign planning."""

from dataclasses import FrozenInstanceError

import pytest

from api.ai_campaign_planner import AICampaignPlannerAPI
from services.ai_campaign_plan import AICampaignObjective, AICampaignPlan
from services.ai_campaign_planner import AICampaignPlanService


def test_plan_models_are_immutable() -> None:
    plan = AICampaignPlan("No Lose Guard", 28, (), ())

    with pytest.raises(FrozenInstanceError):
        plan.duration_days = 14


def test_plan_defaults_have_no_warnings_or_errors() -> None:
    plan = AICampaignPlan("No Lose Guard", 28, (), ())

    assert plan.warnings == ()
    assert plan.errors == ()


def test_service_returns_named_four_week_plan() -> None:
    plan = AICampaignPlanService().plan("No Lose Guard")

    assert plan.campaign_name == "No Lose Guard"
    assert plan.duration_days == 28
    assert tuple(week.number for week in plan.weeks) == (1, 2, 3, 4)


def test_service_returns_objectives_and_tasks() -> None:
    plan = AICampaignPlanService().plan("No Lose Guard")

    assert len(plan.objectives) == 3
    assert all(week.tasks for week in plan.weeks)


def test_service_normalizes_campaign_name() -> None:
    plan = AICampaignPlanService().plan("  No Lose Guard  ")

    assert plan.campaign_name == "No Lose Guard"


def test_service_rejects_empty_campaign_name() -> None:
    with pytest.raises(ValueError, match="campaign_name must not be empty"):
        AICampaignPlanService().plan("   ")


class StubService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def plan(self, campaign_name: str) -> AICampaignPlan:
        self.calls.append(campaign_name)
        return AICampaignPlan(
            campaign_name,
            7,
            (AICampaignObjective("Test objective"),),
            (),
        )


def test_api_delegates_to_injected_service() -> None:
    service = StubService()

    plan = AICampaignPlannerAPI(service).plan("Campaign")

    assert service.calls == ["Campaign"]
    assert plan.duration_days == 7
