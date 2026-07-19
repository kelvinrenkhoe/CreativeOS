from pathlib import Path

import pytest

from ai.mock import MockProvider
from core.project import Project
from services.campaign import CampaignService
from services.campaign_generator import CAMPAIGN_ASSETS, CampaignGeneratorService
from services.prompt_template import PromptTemplateService

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
  genre: Afrobeats
repository:
  songs: songs
  campaigns: campaigns
  books: books
  templates: templates
  assets: assets
  knowledge: knowledge
  media: media
ai:
  provider: mock
  default_model: mock-v1
"""


class RecordingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__(response="# Generated campaign content")
        self.prompts: list[str] = []
        self.system_prompts: list[str | None] = []

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        return super().generate(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )


def create_project(root: Path) -> Project:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    return Project(root)


def test_generate_writes_all_campaign_assets(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    CampaignService(project).create("Now Them Go Hear Me")
    provider = RecordingProvider()

    paths = CampaignGeneratorService(project, provider).generate("Now Them Go Hear Me")

    assert len(paths) == len(CAMPAIGN_ASSETS)
    assert len(provider.prompts) == len(CAMPAIGN_ASSETS)
    assert all(
        path.read_text(encoding="utf-8") == "# Generated campaign content\n" for path in paths
    )


def test_prompt_contains_grounded_campaign_context(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    CampaignService(project).create("Carry Your Name")
    provider = RecordingProvider()

    CampaignGeneratorService(project, provider).generate("Carry Your Name")

    prompt = provider.prompts[0]
    assert "Campaign: Carry Your Name" in prompt
    assert "Artist: Kelvin Rankie" in prompt
    assert "Genre: Afrobeats" in prompt
    assert "Do not invent achievements" in prompt


def test_existing_user_content_is_not_overwritten(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    campaign_path = CampaignService(project).create("Na You")
    protected_path = campaign_path / "captions" / "facebook.md"
    protected_path.write_text("My approved post\n", encoding="utf-8")
    provider = RecordingProvider()

    with pytest.raises(FileExistsError, match="facebook.md"):
        CampaignGeneratorService(project, provider).generate("Na You")

    assert protected_path.read_text(encoding="utf-8") == "My approved post\n"
    assert provider.prompts == []


def test_force_replaces_existing_content(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    campaign_path = CampaignService(project).create("No Break")
    target = campaign_path / "captions" / "instagram.md"
    target.write_text("Old content\n", encoding="utf-8")

    paths = CampaignGeneratorService(project, MockProvider(response="New content")).generate(
        "No Break", force=True
    )

    assert target in paths
    assert target.read_text(encoding="utf-8") == "New content\n"


def test_missing_campaign_is_rejected(tmp_path: Path) -> None:
    project = create_project(tmp_path)

    with pytest.raises(FileNotFoundError, match="missing-campaign"):
        CampaignGeneratorService(project, MockProvider()).generate("Missing Campaign")


def test_generator_uses_injected_prompt_templates(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    CampaignService(project).create("Now Them Go Hear Me")

    template_dir = tmp_path / "prompts"
    template_dir.mkdir()

    for asset in CAMPAIGN_ASSETS:
        (template_dir / f"{asset.template_name}.md").write_text(
            "CUSTOM TEMPLATE\n"
            "Campaign: {{ campaign }}\n"
            "Artist: {{ artist }}\n"
            "Purpose: {{ purpose }}\n",
            encoding="utf-8",
        )

    provider = RecordingProvider()
    templates = PromptTemplateService(template_dir)

    CampaignGeneratorService(
        project,
        provider,
        templates,
    ).generate("Now Them Go Hear Me")

    assert len(provider.prompts) == len(CAMPAIGN_ASSETS)
    assert all("CUSTOM TEMPLATE" in prompt for prompt in provider.prompts)
    assert all("Campaign: Now Them Go Hear Me" in prompt for prompt in provider.prompts)
    assert all("Artist: Kelvin Rankie" in prompt for prompt in provider.prompts)


def test_generator_renders_all_template_placeholders(tmp_path: Path) -> None:
    project = create_project(tmp_path)
    CampaignService(project).create("Carry Your Name")

    template_dir = tmp_path / "prompts"
    template_dir.mkdir()

    for asset in CAMPAIGN_ASSETS:
        (template_dir / f"{asset.template_name}.md").write_text(
            "{{ campaign }} | {{ artist }} | {{ genre }} | {{ purpose }}",
            encoding="utf-8",
        )

    provider = RecordingProvider()

    CampaignGeneratorService(
        project,
        provider,
        PromptTemplateService(template_dir),
    ).generate("Carry Your Name")

    assert provider.prompts
    assert all("Carry Your Name" in prompt for prompt in provider.prompts)
    assert all("Kelvin Rankie" in prompt for prompt in provider.prompts)
    assert all("Afrobeats" in prompt for prompt in provider.prompts)
    assert all("{{" not in prompt and "}}" not in prompt for prompt in provider.prompts)
