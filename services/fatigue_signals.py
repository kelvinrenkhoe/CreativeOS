"""Detect deterministic content, visual, and performance fatigue signals."""

from collections.abc import Iterable
from dataclasses import dataclass

from services.asset_intelligence import NoveltyAssessment
from services.campaign_measurement import (
    CampaignMeasurement,
    CampaignMeasurementService,
)


@dataclass(frozen=True, slots=True)
class CreativeFatigueInput:
    """A novelty assessment tied to one content or visual asset."""

    asset_id: str
    medium: str
    assessment: NoveltyAssessment


@dataclass(frozen=True, slots=True)
class FatigueSignal:
    """One explainable indicator that a campaign may need creative rotation."""

    kind: str
    severity: str
    score: float
    reason: str
    asset_id: str | None = None
    medium: str | None = None
    platform: str | None = None
    metric: str | None = None


@dataclass(frozen=True, slots=True)
class FatigueAssessment:
    """Deterministic fatigue signals for one campaign measurement."""

    campaign_id: str
    signals: tuple[FatigueSignal, ...]

    @property
    def has_fatigue(self) -> bool:
        """Return whether at least one fatigue signal was detected."""
        return bool(self.signals)


class FatigueSignalService:
    """Combine measurement changes and novelty assessments without AI judgement."""

    def __init__(
        self,
        *,
        decline_threshold: float = 20.0,
        severe_decline_threshold: float = 40.0,
    ) -> None:
        if not 0 < decline_threshold <= 100:
            raise ValueError("decline_threshold must be between 0 and 100")
        if not decline_threshold <= severe_decline_threshold <= 100:
            raise ValueError(
                "severe_decline_threshold must be between decline_threshold and 100"
            )
        self.decline_threshold = decline_threshold
        self.severe_decline_threshold = severe_decline_threshold

    def assess(
        self,
        current: CampaignMeasurement,
        baseline: CampaignMeasurement,
        *,
        creative: Iterable[CreativeFatigueInput] = (),
    ) -> FatigueAssessment:
        """Return ordered performance and creative fatigue signals."""
        signals = [
            *self._performance_signals(current, baseline),
            *self._creative_signals(creative),
        ]
        signals.sort(
            key=lambda signal: (
                signal.kind,
                signal.medium or "",
                signal.platform or "",
                signal.metric or "",
                signal.asset_id or "",
            )
        )
        return FatigueAssessment(\n            campaign_id=current.campaign_id, signals=tuple(signals)\n        )

    def _performance_signals(
        self,
        current: CampaignMeasurement,
        baseline: CampaignMeasurement,
    ) -> list[FatigueSignal]:
        comparison = CampaignMeasurementService().compare(current, baseline)
        signals: list[FatigueSignal] = []

        for metric in comparison.metrics:
            change = metric.percentage_change
            if change is None or change > -self.decline_threshold:
                continue
            severity = (
                "high" if change <= -self.severe_decline_threshold else "moderate"
            )
            signals.append(
                FatigueSignal(
                    kind="performance-decline",
                    severity=severity,
                    score=round(abs(change) / 100, 4),
                    platform=metric.platform,
                    metric=metric.metric,
                    reason=(
                        f"{metric.platform} {metric.metric} declined "
                        f"{abs(change):.1f}% from the baseline"
                    ),
                )
            )
        return signals

    @classmethod
    def _creative_signals(
        cls,
        creative: Iterable[CreativeFatigueInput],
    ) -> list[FatigueSignal]:
        signals: list[FatigueSignal] = []
        identities: set[tuple[str, str]] = set()

        for item in creative:
            asset_id = cls._required(item.asset_id, "asset_id")
            medium = cls._medium(item.medium)
            identity = (asset_id, medium)
            if identity in identities:
                raise ValueError("duplicate creative fatigue input")
            identities.add(identity)

            if not item.assessment.is_repetitive:
                continue
            signals.append(
                FatigueSignal(
                    kind=f"{medium}-repetition",
                    severity=(
                        "high"
                        if item.assessment.similarity_score >= 0.9
                        else "moderate"
                    ),
                    score=item.assessment.similarity_score,
                    asset_id=asset_id,
                    medium=medium,
                    reason=(
                        f"{medium} pattern is "
                        f"{item.assessment.similarity_score:.1%} similar "
                        "to a prior campaign asset"
                    ),
                )
            )
        return signals

    @classmethod
    def _medium(cls, value: str) -> str:
        normalized = cls._required(value, "medium").casefold()
        if normalized not in {"content", "visual"}:
            raise ValueError("medium must be content or visual")
        return normalized

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
