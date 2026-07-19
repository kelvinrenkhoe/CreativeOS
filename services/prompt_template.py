"""Utilities for loading CreativeOS prompt templates."""

from pathlib import Path


class PromptTemplateService:
    """Load prompt templates from the prompts directory."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self._template_dir = template_dir or Path("prompts")

    def load(self, template_name: str) -> str:
        """Load a prompt template by name."""
        template_path = self._template_dir / f"{template_name}.md"

        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template '{template_name}' was not found.")

        return template_path.read_text(encoding="utf-8")
