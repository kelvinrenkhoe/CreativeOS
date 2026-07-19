"""AI-powered campaign content generation service."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from ai.provider import AIProvider
from core.project import Project
from services.campaign import DEFAULT_FILES, slugify
from services.prompt_template import PromptTemplateService


@dataclass(frozen=True, slots=True)
class CampaignAsset:
    """A generated campaign asset and its destination."""

    relative_path: str
    purpose: str
    template_name: str


CAMPAIGN_ASSETS = (
    CampaignAsset(
        "captions/instagram.md",
        "Instagram launch caption",
        "instagram",
    ),
    CampaignAsset(
        "captions/facebook.md",
        "Facebook launch post",
        "facebook",
    ),
    CampaignAsset(
        "captions/tiktok.md",
        "TikTok video caption",
        "tiktok",
    ),
    CampaignAsset(
        "captions/x.md",
        "X launch post",
        "x",
    ),
    CampaignAsset(
        "radio/pitch.md",
        "radio presenter and DJ pitch",
        "radio_pitch",
    ),
    CampaignAsset(
        "playlist/pitch.md",
        "playlist curator pitch",
        "playlist_pitch",
    ),
    CampaignAsset(
        "press/press-release.md",
        "music press release",
        "press_release",
    ),
    CampaignAsset(
        "schedule/content-calendar.md",
        "four-week content calendar",
        "content_calendar",
    ),
)


class CampaignGeneratorService:
    """Generate campaign assets using a configured AI provider."""

    def __init__(
        self,
        project: Project,
        provider: AIProvider,
        templates: PromptTemplateService | None = None,
    ) -> None:
        self.project = project
        self.provider = provider
        self.templates = templates or PromptTemplateService()

    def generate(self, name: str, *, force: bool = False) -> tuple[Path, ...]:
        """Generate campaign files and return the paths that were written."""
        campaign_path = self.project.campaigns_path / slugify(name)
        manifest_path = campaign_path / "campaign.yaml"

        if not manifest_path.is_file():
            raise FileNotFoundError(f"Campaign not found: {campaign_path.name}")

        manifest = self._load_manifest(manifest_path)
        destinations = tuple(campaign_path / asset.relative_path for asset in CAMPAIGN_ASSETS)

        conflicts = [
            asset.relative_path
            for asset, destination in zip(CAMPAIGN_ASSETS, destinations, strict=True)
            if self._contains_user_content(destination, asset.relative_path) and not force
        ]

        if conflicts:
            raise FileExistsError(
                "Campaign assets already contain content: "
                f"{', '.join(conflicts)}. Use --force to replace them."
            )

        written: list[Path] = []

        for asset, destination in zip(CAMPAIGN_ASSETS, destinations, strict=True):
            destination.parent.mkdir(parents=True, exist_ok=True)

            prompt = self._build_prompt(manifest, asset)
            response = self.provider.generate(
                prompt,
                system_prompt=(
                    "You are an experienced music marketing strategist. "
                    "Write practical, release-ready content in Markdown."
                ),
            )

            destination.write_text(response.strip() + "\n", encoding="utf-8")
            written.append(destination)

        return tuple(written)

    @staticmethod
    def _contains_user_content(path: Path, relative_path: str) -> bool:
        if not path.exists():
            return False

        content = path.read_text(encoding="utf-8")
        placeholder = DEFAULT_FILES.get(relative_path, "")
        return bool(content.strip()) and content != placeholder

    @staticmethod
    def _load_manifest(path: Path) -> dict[str, object]:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid campaign manifest: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Campaign manifest must be a YAML mapping.")

        if not data.get("name") or not data.get("artist"):
            raise ValueError("Campaign manifest requires name and artist.")

        return data

    def _build_prompt(
        self,
        manifest: dict[str, object],
        asset: CampaignAsset,
    ) -> str:
        """Render the prompt template for a campaign asset."""
        campaign_name = str(manifest["name"])
        goals = manifest.get("goals") or {}

        context: dict[str, object] = {
            "purpose": asset.purpose,
            "campaign": campaign_name,
            "name": campaign_name,
            "song": campaign_name,
            "artist": manifest["artist"],
            "genre": self.project.genre or "Not specified",
            "release_date": manifest.get("release_date") or "Not specified",
            "spotify": manifest.get("spotify") or "Not specified",
            "smart_link": manifest.get("smart_link") or "Not specified",
            "hashtags": manifest.get("hashtags") or [],
            "platforms": manifest.get("platforms") or [],
            "goals": goals,
            "audience": manifest.get("audience") or "Not specified",
            "tone": manifest.get("tone") or "Confident and authentic",
            "objective": manifest.get("objective") or goals or "Promote the music release",
        }

        return self.templates.render(asset.template_name, context)
