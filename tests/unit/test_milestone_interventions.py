from services.daily_brief import DailyBriefService, MilestoneAttention


def attention(
    *,
    blocked: int = 0,
    pending: int = 0,
    days: int = 5,
) -> MilestoneAttention:
    return MilestoneAttention(
        name="launch",
        status="at-risk",
        reason="needs attention",
        days_from_brief=days,
        completed=1,
        total=3,
        pending=pending,
        blocked=blocked,
    )


def test_intervention_prioritises_blocked_and_pending_work() -> None:
    result = DailyBriefService._milestone_interventions((attention(blocked=1, pending=1),))

    assert result[0].suggestion == "Resolve blocked work, then review dependency-waiting actions."


def test_intervention_handles_blocked_work() -> None:
    result = DailyBriefService._milestone_interventions((attention(blocked=1),))

    assert "Resolve blocked milestone work" in result[0].suggestion


def test_intervention_handles_dependency_waiting_work() -> None:
    result = DailyBriefService._milestone_interventions((attention(pending=1),))

    assert "dependency-waiting actions" in result[0].suggestion


def test_intervention_handles_overdue_incomplete_work() -> None:
    result = DailyBriefService._milestone_interventions((attention(days=-1),))

    assert "overdue work" in result[0].suggestion


def test_intervention_handles_imminent_remaining_work() -> None:
    result = DailyBriefService._milestone_interventions((attention(days=2),))

    assert "imminent deadline" in result[0].suggestion


def test_interventions_preserve_attention_order() -> None:
    first = attention(blocked=1)
    second = MilestoneAttention(
        name="review",
        status="watch",
        reason="needs attention",
        days_from_brief=7,
        completed=0,
        total=1,
        pending=0,
        blocked=0,
    )

    result = DailyBriefService._milestone_interventions((first, second))

    assert [item.name for item in result] == ["launch", "review"]
