from services.daily_brief import (
    DailyBriefService,
    MilestoneAttention,
    MilestoneHealth,
    MilestoneIntervention,
)


def test_campaign_decision_uses_highest_priority_attention() -> None:
    health = (
        MilestoneHealth("launch", "at-risk", "deadline passed with incomplete work"),
        MilestoneHealth("review", "watch", "deadline is within seven days with incomplete work"),
    )
    attention = (
        MilestoneAttention("launch", "at-risk", "deadline passed with incomplete work", -1, 1, 3, 1, 1),
        MilestoneAttention(
            "review",
            "watch",
            "deadline is within seven days with incomplete work",
            6,
            0,
            2,
            0,
            0,
        ),
    )
    interventions = (
        MilestoneIntervention("launch", "at-risk", "Resolve blocked work."),
        MilestoneIntervention("review", "watch", "Review remaining work."),
    )

    decision = DailyBriefService._campaign_decision(health, attention, interventions)

    assert decision.status == "at-risk"
    assert decision.milestone == "launch"
    assert decision.reason == "deadline passed with incomplete work"
    assert decision.suggestion == "Resolve blocked work."


def test_campaign_decision_reports_watch_state() -> None:
    health = (MilestoneHealth("launch", "watch", "linked work is blocked"),)
    attention = (
        MilestoneAttention("launch", "watch", "linked work is blocked", 10, 0, 2, 0, 1),
    )
    interventions = (
        MilestoneIntervention("launch", "watch", "Resolve blocked milestone work."),
    )

    decision = DailyBriefService._campaign_decision(health, attention, interventions)

    assert decision.status == "watch"
    assert decision.milestone == "launch"


def test_campaign_decision_reports_complete() -> None:
    decision = DailyBriefService._campaign_decision(
        (MilestoneHealth("launch", "complete", "all linked actions completed"),),
        (),
        (),
    )

    assert decision.status == "complete"
    assert decision.milestone is None


def test_campaign_decision_reports_on_track() -> None:
    health = (
        MilestoneHealth("freeze", "complete", "all linked actions completed"),
        MilestoneHealth(
            "launch",
            "on-track",
            "remaining work is not currently deadline-constrained",
        ),
    )

    decision = DailyBriefService._campaign_decision(health, (), ())

    assert decision.status == "on-track"
    assert decision.suggestion == "Continue with the existing execution plan."


def test_campaign_decision_reports_untracked() -> None:
    decision = DailyBriefService._campaign_decision(
        (MilestoneHealth("launch", "untracked", "no linked actions"),),
        (),
        (),
    )

    assert decision.status == "untracked"
    assert "Link executable campaign actions" in decision.suggestion
