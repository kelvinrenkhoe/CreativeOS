"""Deterministic campaign quality scoring."""

from collections import defaultdict

from models.campaign_score import CampaignScore, CampaignScoreCategory
from models.doctor import DoctorCheck, DoctorReport


class CampaignScoringService:
    """Convert Campaign Doctor results into campaign quality scores."""

    def score(
        self,
        campaign_name: str,
        report: DoctorReport,
    ) -> CampaignScore:
        """Return deterministic overall and category scores."""
        grouped: dict[str, list[DoctorCheck]] = defaultdict(list)

        for check in report.checks:
            grouped[check.category].append(check)

        categories = tuple(
            self._score_category(name, tuple(checks)) for name, checks in grouped.items()
        )

        overall_score = self._overall_score(categories)

        return CampaignScore(
            campaign_name=campaign_name.strip(),
            overall_score=overall_score,
            categories=categories,
        )

    @staticmethod
    def _score_category(
        name: str,
        checks: tuple[DoctorCheck, ...],
    ) -> CampaignScoreCategory:
        """Score one Doctor category."""
        total = len(checks)
        passed = sum(check.passed for check in checks)
        score = 100 if total == 0 else passed * 100 // total

        findings = tuple(f"{check.name}: {check.detail}" for check in checks if not check.passed)

        return CampaignScoreCategory(
            name=name,
            score=score,
            passed_checks=passed,
            total_checks=total,
            findings=findings,
        )

    @staticmethod
    def _overall_score(
        categories: tuple[CampaignScoreCategory, ...],
    ) -> int:
        """Return a check-weighted overall score."""
        total_checks = sum(category.total_checks for category in categories)

        if total_checks == 0:
            return 100

        passed_checks = sum(category.passed_checks for category in categories)

        return passed_checks * 100 // total_checks
