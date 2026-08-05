"""Immutable models for creator-facing AI campaign plans."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AICampaignTask:
    """One actionable task in a generated campaign week."""

    title: str
    description: str


@dataclass(frozen=True, slots=True)
class AICampaignWeek:
    """One numbered week and its campaign objective."""

    number: int
    objective: str
    tasks: tuple[AICampaignTask, ...]


@dataclass(frozen=True, slots=True)
class AICampaignObjective:
    """One measurable campaign objective."""

    title: str


@dataclass(frozen=True, slots=True)
class AICampaignPlan:
    """A structured creator-facing rollout plan."""

    campaign_name: str
    duration_days: int
    objectives: tuple[AICampaignObjective, ...]
    weeks: tuple[AICampaignWeek, ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
