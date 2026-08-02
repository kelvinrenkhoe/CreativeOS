"""Immutable models for deterministic scene-aligned voice-over scripts."""

from dataclasses import dataclass
from enum import StrEnum


class VoiceoverError(ValueError):
    """Reject invalid or inconsistent voice-over input."""


class VoiceoverStyle(StrEnum):
    REFLECTIVE = "reflective"
    CONVERSATIONAL = "conversational"
    MOTIVATIONAL = "motivational"
    CINEMATIC = "cinematic"


class NarrationPace(StrEnum):
    SLOW = "slow"
    MEASURED = "measured"
    MODERATE = "moderate"
    ENERGETIC = "energetic"


@dataclass(frozen=True, slots=True)
class VoiceoverSegment:
    scene_number: int
    duration_seconds: int
    narration: str
    style: VoiceoverStyle
    pace: NarrationPace
    emphasis: tuple[str, ...]
    pause_after_seconds: float

    def __post_init__(self) -> None:
        if self.scene_number < 1:
            raise VoiceoverError("scene_number must be at least 1")
        if self.duration_seconds < 1:
            raise VoiceoverError("duration_seconds must be at least 1")
        narration = self.narration.strip()
        if not narration:
            raise VoiceoverError("narration must be a non-empty string")
        emphasis = tuple(item.strip() for item in self.emphasis)
        if any(not item for item in emphasis):
            raise VoiceoverError("emphasis must contain non-empty strings")
        if self.pause_after_seconds < 0:
            raise VoiceoverError("pause_after_seconds must not be negative")
        object.__setattr__(self, "narration", narration)
        object.__setattr__(self, "emphasis", emphasis)


@dataclass(frozen=True, slots=True)
class VoiceoverScript:
    script_id: str
    campaign_id: str
    campaign_name: str
    campaign_week: int
    title: str
    tone: str
    audience: str
    call_to_action: str
    segments: tuple[VoiceoverSegment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise VoiceoverError("segments must not be empty")
        expected = tuple(range(1, len(self.segments) + 1))
        actual = tuple(segment.scene_number for segment in self.segments)
        if actual != expected:
            raise VoiceoverError("segments must be numbered sequentially")

    @property
    def total_duration_seconds(self) -> int:
        return sum(segment.duration_seconds for segment in self.segments)

    def render(self) -> str:
        lines = [
            f"# Voice-over: {self.title}",
            "",
            f"Campaign: {self.campaign_name}",
            f"Week: {self.campaign_week}",
            f"Duration: {self.total_duration_seconds}s",
            f"Tone: {self.tone}",
            f"Audience: {self.audience}",
        ]
        for segment in self.segments:
            lines.extend(
                (
                    "",
                    f"## Scene {segment.scene_number} — {segment.duration_seconds}s",
                    f"Narration: {segment.narration}",
                    f"Style: {segment.style.value}",
                    f"Pace: {segment.pace.value}",
                    f"Emphasis: {', '.join(segment.emphasis) or 'none'}",
                    f"Pause after: {segment.pause_after_seconds:g}s",
                )
            )
        lines.extend(("", "## Call to action", self.call_to_action))
        return "\n".join(lines)
