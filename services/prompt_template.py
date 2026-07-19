"""Utilities for loading and rendering CreativeOS prompt templates."""

from pathlib import Path


class PromptTemplateService:
    """Load and render prompt templates."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self._template_dir = template_dir or Path("prompts")

    def load(self, template_name: str) -> str:
        """Load a prompt template."""
        template_path = self._template_dir / f"{template_name}.md"

        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template '{template_name}' was not found.")

        return template_path.read_text(encoding="utf-8")

    def render(
        self,
        template_name: str,
        context: dict[str, object],
    ) -> str:
        """Render a prompt template using placeholder replacement."""
        template = self.load(template_name)

        for key, value in context.items():
            template = template.replace(
                f"{{{{ {key} }}}}",
                str(value),
            )

        return template
