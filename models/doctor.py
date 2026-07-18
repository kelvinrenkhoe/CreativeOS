"""Models used by the CreativeOS doctor command."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DoctorCheck:
    """Result of one CreativeOS health check."""

    category: str
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class DoctorReport:
    """Complete CreativeOS health report."""

    checks: tuple[DoctorCheck, ...]

    @property
    def healthy(self) -> bool:
        """Return True when every health check passes."""
        return all(check.passed for check in self.checks)

    @property
    def passed_count(self) -> int:
        """Return the number of successful checks."""
        return sum(check.passed for check in self.checks)

    @property
    def failed_count(self) -> int:
        """Return the number of failed checks."""
        return len(self.checks) - self.passed_count
