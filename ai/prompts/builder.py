"""Deterministic section-based prompt construction."""

from dataclasses import dataclass, field


class PromptValidationError(ValueError):
    """Reject incomplete or empty prompt definitions."""


@dataclass(slots=True)
class PromptBuilder:
    """Build validated prompts from named sections in a stable order."""

    _system: str = ""
    _instruction: str = ""
    _context: list[str] = field(default_factory=list)
    _constraints: list[str] = field(default_factory=list)

    def system(self, value: str) -> "PromptBuilder":
        self._system = self._clean(value, "system prompt")
        return self

    def instruction(self, value: str) -> "PromptBuilder":
        self._instruction = self._clean(value, "instruction")
        return self

    def context(self, value: str) -> "PromptBuilder":
        self._context.append(self._clean(value, "context"))
        return self

    def constraint(self, value: str) -> "PromptBuilder":
        self._constraints.append(self._clean(value, "constraint"))
        return self

    @property
    def system_prompt(self) -> str:
        """Return the validated system prompt for provider calls."""
        if not self._system:
            raise PromptValidationError("system prompt is required")
        return self._system

    def render(self) -> str:
        """Render non-system sections in deterministic order."""
        if not self._system:
            raise PromptValidationError("system prompt is required")
        if not self._instruction:
            raise PromptValidationError("instruction is required")

        sections = [f"## Instruction\n{self._instruction}"]
        if self._context:
            sections.append("## Context\n" + "\n".join(self._context))
        if self._constraints:
            constraints = "\n".join(f"- {item}" for item in self._constraints)
            sections.append(f"## Constraints\n{constraints}")
        return "\n\n".join(sections)

    @staticmethod
    def _clean(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PromptValidationError(f"{field_name} must not be empty")
        return " ".join(value.split())
