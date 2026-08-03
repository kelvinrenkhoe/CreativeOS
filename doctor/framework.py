"""Registration and execution framework for CreativeOS Doctor checks."""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from models.doctor import DoctorCheck


@runtime_checkable
class DoctorCheckProvider(Protocol):
    """Contract implemented by an independently registered health check."""

    @property
    def name(self) -> str:
        """Return the stable provider name used for registration."""

    def run(self) -> DoctorCheck | tuple[DoctorCheck, ...]:
        """Run the provider and return one or more health-check results."""


class DoctorCheckRegistry:
    """Store and execute doctor-check providers in registration order."""

    def __init__(self, providers: Iterable[DoctorCheckProvider] = ()) -> None:
        self._providers: dict[str, DoctorCheckProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: DoctorCheckProvider) -> None:
        """Register one provider and reject duplicate or blank names."""
        name = provider.name.strip()
        if not name:
            raise ValueError("doctor check provider name must not be empty")
        if name in self._providers:
            raise ValueError(f"doctor check provider already registered: {name}")
        self._providers[name] = provider

    @property
    def names(self) -> tuple[str, ...]:
        """Return provider names in deterministic registration order."""
        return tuple(self._providers)

    def run_all(self) -> tuple[DoctorCheck, ...]:
        """Run all providers while isolating failures to their own result."""
        checks: list[DoctorCheck] = []
        for name, provider in self._providers.items():
            try:
                result = provider.run()
            except Exception as exc:  # noqa: BLE001
                checks.append(
                    DoctorCheck(
                        category="Extensions",
                        name=name,
                        passed=False,
                        detail=f"Provider failed: {exc}",
                    )
                )
                continue

            provider_checks = result if isinstance(result, tuple) else (result,)
            if not provider_checks:
                checks.append(
                    DoctorCheck(
                        category="Extensions",
                        name=name,
                        passed=False,
                        detail="Provider returned no checks",
                    )
                )
                continue
            if not all(isinstance(check, DoctorCheck) for check in provider_checks):
                checks.append(
                    DoctorCheck(
                        category="Extensions",
                        name=name,
                        passed=False,
                        detail="Provider returned an invalid check result",
                    )
                )
                continue
            checks.extend(provider_checks)

        return tuple(checks)
