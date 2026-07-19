from pathlib import Path

import pytest

from services.prompt_template import PromptTemplateService


def test_load_template(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    (prompts / "instagram.md").write_text(
        "Hello Template",
        encoding="utf-8",
    )

    service = PromptTemplateService(prompts)

    assert service.load("instagram") == "Hello Template"


def test_render_template(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    (prompts / "instagram.md").write_text(
        "Artist: {{ artist }}\nSong: {{ song }}",
        encoding="utf-8",
    )

    service = PromptTemplateService(prompts)

    rendered = service.render(
        "instagram",
        {
            "artist": "Kelvin Rankie",
            "song": "Now Them Go Hear Me",
        },
    )

    assert "Kelvin Rankie" in rendered
    assert "Now Them Go Hear Me" in rendered


def test_missing_template(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    service = PromptTemplateService(prompts)

    with pytest.raises(FileNotFoundError):
        service.load("missing")
