"""Models used by the CreativeOS doctor command."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DoctorCheck:
    """Result of one CreativeOS health check."""

    category: str
    name: str
    passed: bool
    detail: str = ""
    required: bool = True

    @property
    def warning(self) -> bool:
        """Return True when an optional check did not pass."""
        return not self.passed and not self.required

    @property
    def failed(self) -> bool:
        """Return True when a required check did not pass."""
        return not self.passed and self.required


@dataclass(frozen=True)
class DoctorReport:
    """Complete CreativeOS health report."""

    checks: tuple[DoctorCheck, ...]

    @property
    def healthy(self) -> bool:
        """Return True when no required health check fails."""
        return self.failed_count == 0

    @property
    def passed_count(self) -> int:
        """Return the number of successful checks."""
        return sum(check.passed for check in self.checks)

    @property
    def warning_count(self) -> int:
        """Return the number of optional checks that did not pass."""
        return sum(check.warning for check in self.checks)

    @property
    def failed_count(self) -> int:
        """Return the number of required checks that failed."""
        return sum(check.failed for check in self.checks)

    @property
    def health_score(self) -> int:
        """Return the percentage of all checks that passed."""
        if not self.checks:
            return 100
        return self.passed_count * 100 // len(self.checks)
