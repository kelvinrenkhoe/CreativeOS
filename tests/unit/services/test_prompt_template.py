from pathlib import Path

import pytest

from services.prompt_template import PromptTemplateService


def test_load_template(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    template = prompts / "instagram.md"
    template.write_text("Hello Template", encoding="utf-8")

    service = PromptTemplateService(prompts)

    assert service.load("instagram") == "Hello Template"


def test_missing_template(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    service = PromptTemplateService(prompts)

    with pytest.raises(FileNotFoundError):
        service.load("missing")
