"""Build validated AI campaign plans behind a stable service contract."""

import json
from collections.abc import Mapping
from typing import Any

from ai.prompts import PromptBuilder
from ai.provider import AIProvider
from services.ai_campaign_plan import (
    AICampaignObjective,
    AICampaignPlan,
    AICampaignTask,
    AICampaignWeek,
)


class AICampaignPlanService:
    """Build deterministic or provider-generated creator-facing rollout plans."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider

    def plan(self, campaign_name: str) -> AICampaignPlan:
        """Build a validated four-week creator-facing rollout plan."""
        name = campaign_name.strip()
        if not name:
            raise ValueError("campaign_name must not be empty")
        if self.provider is None:
            return self._deterministic_plan(name)

        try:
            prompt = self._prompt(name)
            response = self.provider.generate(
                prompt.render(),
                system_prompt=prompt.system_prompt,
                temperature=0.4,
            )
            return self._parse(name, response)
        except Exception as exc:  # provider boundaries must not crash callers
            return self._error_plan(name, f"AI campaign planner failed: {exc}")

    @staticmethod
    def _prompt(campaign_name: str) -> PromptBuilder:
        return (
            PromptBuilder()
            .system(
                "You are an expert campaign strategist for independent creators. "
                "Return valid JSON only."
            )
            .instruction("Create a practical 28-day marketing rollout.")
            .context(f'Campaign: "{campaign_name}"')
            .constraint(
                'Return one JSON object with exactly these fields: "campaign_name", '
                '"duration_days", "objectives", and "weeks".'
            )
            .constraint('"objectives" must be a non-empty array of strings.')
            .constraint(
                '"weeks" must contain four objects with integer "number", non-empty '
                '"objective", and a non-empty "tasks" array.'
            )
            .constraint(
                'Each task must contain non-empty "title" and "description" strings.'
            )
            .constraint("Do not include Markdown or commentary.")
        )

    @classmethod
    def _parse(cls, requested_name: str, response: str) -> AICampaignPlan:
        try:
            payload = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return cls._error_plan(requested_name, "Planner returned malformed JSON")

        if not isinstance(payload, Mapping):
            return cls._error_plan(requested_name, "Planner returned invalid structure")

        try:
            campaign_name = cls._required_text(payload.get("campaign_name"), "campaign_name")
            duration_days = payload.get("duration_days")
            if not isinstance(duration_days, int) or isinstance(duration_days, bool):
                raise ValueError("duration_days must be an integer")
            if duration_days < 1:
                raise ValueError("duration_days must be greater than zero")

            objectives_value = payload.get("objectives")
            if not isinstance(objectives_value, list) or not objectives_value:
                raise ValueError("objectives must be a non-empty array")
            objectives = tuple(
                AICampaignObjective(cls._required_text(value, "objective"))
                for value in objectives_value
            )

            weeks_value = payload.get("weeks")
            if not isinstance(weeks_value, list) or not weeks_value:
                raise ValueError("weeks must be a non-empty array")
            weeks = tuple(cls._week(value) for value in weeks_value)
        except ValueError as exc:
            return cls._error_plan(requested_name, f"Planner returned invalid structure: {exc}")

        warnings = ()
        if campaign_name.casefold() != requested_name.casefold():
            warnings = ("Provider campaign name differed from the requested campaign",)

        return AICampaignPlan(
            campaign_name=campaign_name,
            duration_days=duration_days,
            objectives=objectives,
            weeks=weeks,
            warnings=warnings,
        )

    @classmethod
    def _week(cls, value: Any) -> AICampaignWeek:
        if not isinstance(value, Mapping):
            raise ValueError("each week must be an object")
        number = value.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ValueError("week number must be a positive integer")
        objective = cls._required_text(value.get("objective"), "week objective")
        tasks_value = value.get("tasks")
        if not isinstance(tasks_value, list) or not tasks_value:
            raise ValueError("week tasks must be a non-empty array")
        tasks = tuple(cls._task(task) for task in tasks_value)
        return AICampaignWeek(number=number, objective=objective, tasks=tasks)

    @classmethod
    def _task(cls, value: Any) -> AICampaignTask:
        if not isinstance(value, Mapping):
            raise ValueError("each task must be an object")
        return AICampaignTask(
            title=cls._required_text(value.get("title"), "task title"),
            description=cls._required_text(value.get("description"), "task description"),
        )

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _error_plan(campaign_name: str, error: str) -> AICampaignPlan:
        return AICampaignPlan(
            campaign_name=campaign_name,
            duration_days=0,
            objectives=(),
            weeks=(),
            errors=(error,),
        )

    @staticmethod
    def _deterministic_plan(name: str) -> AICampaignPlan:
        return AICampaignPlan(
            campaign_name=name,
            duration_days=28,
            objectives=(
                AICampaignObjective("Increase release awareness"),
                AICampaignObjective("Grow engaged listeners"),
                AICampaignObjective("Convert attention into streams and saves"),
            ),
            weeks=(
                AICampaignWeek(
                    number=1,
                    objective="Introduce the campaign and build curiosity",
                    tasks=(
                        AICampaignTask("Campaign announcement", "Introduce the release story."),
                        AICampaignTask("Cover reveal", "Share the artwork and central message."),
                    ),
                ),
                AICampaignWeek(
                    number=2,
                    objective="Build recognition around the strongest hook",
                    tasks=(
                        AICampaignTask("Hook videos", "Publish short vertical hook variations."),
                        AICampaignTask("Behind the scenes", "Show the creative process."),
                    ),
                ),
                AICampaignWeek(
                    number=3,
                    objective="Drive discovery and release intent",
                    tasks=(
                        AICampaignTask("Playlist outreach", "Pitch relevant playlists and DJs."),
                        AICampaignTask("Fan prompt", "Invite listeners to react or participate."),
                    ),
                ),
                AICampaignWeek(
                    number=4,
                    objective="Sustain momentum and deepen connection",
                    tasks=(
                        AICampaignTask(
                            "Performance content",
                            "Share a live or stripped-back clip.",
                        ),
                        AICampaignTask(
                            "Thank-you post",
                            "Celebrate listeners and early supporters.",
                        ),
                    ),
                ),
            ),
        )
