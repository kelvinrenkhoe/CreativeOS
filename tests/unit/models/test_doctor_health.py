"""Tests for severity-aware CreativeOS doctor reports."""

from models.doctor import DoctorCheck, DoctorReport


def test_optional_missing_check_is_warning_not_failure() -> None:
    check = DoctorCheck(
        category="Repository",
        name="media/",
        passed=False,
        required=False,
    )

    assert check.warning is True
    assert check.failed is False


def test_required_missing_check_is_failure() -> None:
    check = DoctorCheck(
        category="Repository",
        name="songs/",
        passed=False,
    )

    assert check.warning is False
    assert check.failed is True


def test_report_remains_healthy_with_optional_warnings() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck("Workspace", "Configuration", True),
            DoctorCheck("Repository", "media/", False, required=False),
        )
    )

    assert report.healthy is True
    assert report.passed_count == 1
    assert report.warning_count == 1
    assert report.failed_count == 0
    assert report.health_score == 50


def test_report_is_unhealthy_when_required_check_fails() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck("Workspace", "Configuration", True),
            DoctorCheck("Repository", "songs/", False),
            DoctorCheck("Repository", "media/", False, required=False),
        )
    )

    assert report.healthy is False
    assert report.passed_count == 1
    assert report.warning_count == 1
    assert report.failed_count == 1
    assert report.health_score == 33


def test_empty_report_has_full_health_score() -> None:
    report = DoctorReport(checks=())

    assert report.healthy is True
    assert report.health_score == 100
