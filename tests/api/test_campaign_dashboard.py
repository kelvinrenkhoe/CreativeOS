"""Tests for the campaign dashboard aggregation API."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from api.campaign_dashboard import CampaignDashboardAPI
from core.project import Project

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
repository:
  songs: songs
  campaigns: campaigns
  assets: assets
  knowledge: knowledge
"""
DEFAULT_REPORT = object()


def project(root: Path) -> Project:
    """Create a minimum CreativeOS project."""
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir()
    return Project(root)


class StubAnalytics:
    def __init__(self, **changes) -> None:
        values = {
            "readiness_score": 83,
            "health": "on-track",
            "warnings": (),
            "errors": (),
        }
        values.update(changes)
        self.result = SimpleNamespace(**values)
        self.today = None

    def summary(self, _campaign, *, today):
        self.today = today
        return self.result


class StubTasks:
    def __init__(self, **changes) -> None:
        values = {
            "completion_percent": 60,
            "overdue": (object(), object()),
            "due_today": (object(),),
            "warnings": (),
            "errors": (),
        }
        values.update(changes)
        self.result = SimpleNamespace(**values)
        self.reference_date = None

    def today(self, _campaign, *, today):
        self.reference_date = today
        return self.result


class StubTimeline:
    def __init__(self, **changes) -> None:
        values = {
            "current_phase": "Promotion",
            "next_milestone": "Cover artwork reveal",
            "warnings": (),
            "errors": (),
        }
        values.update(changes)
        self.result = SimpleNamespace(**values)
        self.today = None

    def status(self, _campaign, *, today):
        self.today = today
        return self.result


class StubDoctor:
    def __init__(self, report=DEFAULT_REPORT, error: ValueError | None = None) -> None:
        self.report = report
        self.error = error

    def diagnose(self, _campaign, *, context):
        assert context["campaign"]
        if self.error is not None:
            raise self.error
        return self.report


class StubScoring:
    def __init__(self, score: int = 91) -> None:
        self.value = score

    def score(self, _campaign, _report):
        return SimpleNamespace(overall_score=self.value)


class StubRecommendations:
    def __init__(self, count: int = 3) -> None:
        self.items = tuple(object() for _ in range(count))

    def recommend(self, _campaign, _report):
        return SimpleNamespace(items=self.items)


def dashboard(tmp_path: Path, **dependencies) -> CampaignDashboardAPI:
    """Return a dashboard with deterministic test doubles."""
    defaults = {
        "analytics_api": StubAnalytics(),
        "tasks_api": StubTasks(),
        "timeline_api": StubTimeline(),
        "doctor_service": StubDoctor(),
        "scoring_service": StubScoring(),
        "recommendations_service": StubRecommendations(),
    }
    defaults.update(dependencies)
    return CampaignDashboardAPI(project(tmp_path), **defaults)


def test_summary_aggregates_campaign_sources(tmp_path: Path) -> None:
    result = dashboard(tmp_path).summary(
        "No Lose Guard",
        today=date(2026, 8, 4),
    )

    assert result.successful
    assert result.readiness_score == 83
    assert result.readiness_label == "on-track"
    assert result.quality_score == 91
    assert result.current_phase == "Promotion"
    assert result.completion_percent == 60
    assert result.overdue_task_count == 2
    assert result.due_today_count == 1
    assert result.next_milestone == "Cover artwork reveal"
    assert result.recommendation_count == 3


def test_summary_passes_same_reference_date_to_every_api(tmp_path: Path) -> None:
    analytics = StubAnalytics()
    tasks = StubTasks()
    timeline = StubTimeline()
    reference = date(2026, 8, 4)

    dashboard(
        tmp_path,
        analytics_api=analytics,
        tasks_api=tasks,
        timeline_api=timeline,
    ).summary("No Lose Guard", today=reference)

    assert analytics.today == reference
    assert tasks.reference_date == reference
    assert timeline.today == reference


def test_summary_aggregates_and_deduplicates_warnings(tmp_path: Path) -> None:
    result = dashboard(
        tmp_path,
        analytics_api=StubAnalytics(warnings=("Shared warning",)),
        tasks_api=StubTasks(warnings=("Shared warning", "Task warning")),
        timeline_api=StubTimeline(warnings=("Timeline warning",)),
    ).summary("No Lose Guard", today=date(2026, 8, 4))

    assert result.warnings == (
        "Shared warning",
        "Task warning",
        "Timeline warning",
    )
    assert result.warning_count == 3


def test_summary_aggregates_errors_and_preserves_partial_data(tmp_path: Path) -> None:
    result = dashboard(
        tmp_path,
        analytics_api=StubAnalytics(errors=("Analytics failed",)),
        tasks_api=StubTasks(errors=("Tasks failed",)),
    ).summary("No Lose Guard", today=date(2026, 8, 4))

    assert not result.successful
    assert result.errors == ("Analytics failed", "Tasks failed")
    assert result.error_count == 2
    assert result.current_phase == "Promotion"
    assert result.quality_score == 91


def test_summary_reports_campaign_assessment_failure(tmp_path: Path) -> None:
    result = dashboard(
        tmp_path,
        doctor_service=StubDoctor(error=ValueError("invalid campaign")),
    ).summary("No Lose Guard", today=date(2026, 8, 4))

    assert not result.successful
    assert result.quality_score == 0
    assert result.recommendation_count == 0
    assert result.errors == ("Campaign assessment failed: invalid campaign",)


def test_summary_handles_empty_campaign_data(tmp_path: Path) -> None:
    result = dashboard(
        tmp_path,
        analytics_api=StubAnalytics(readiness_score=0, health="needs-attention"),
        tasks_api=StubTasks(
            completion_percent=0,
            overdue=(),
            due_today=(),
        ),
        timeline_api=StubTimeline(
            current_phase="Planning",
            next_milestone=None,
        ),
        scoring_service=StubScoring(score=0),
        recommendations_service=StubRecommendations(count=0),
    ).summary("Empty Campaign", today=date(2026, 8, 4))

    assert result.successful
    assert result.readiness_score == 0
    assert result.quality_score == 0
    assert result.completion_percent == 0
    assert result.next_milestone is None
    assert result.recommendation_count == 0


def test_summary_uses_injected_score_and_recommendation_results(tmp_path: Path) -> None:
    result = dashboard(
        tmp_path,
        scoring_service=StubScoring(score=47),
        recommendations_service=StubRecommendations(count=7),
    ).summary("No Lose Guard", today=date(2026, 8, 4))

    assert result.quality_score == 47
    assert result.recommendation_count == 7
