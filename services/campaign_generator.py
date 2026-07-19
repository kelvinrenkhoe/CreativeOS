"""AI-powered campaign content generation service."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from ai.provider import AIProvider
from core.project import Project
from services.campaign import DEFAULT_FILES, slugify


@dataclass(frozen=True, slots=True)
class CampaignAsset:
    """A generated campaign asset and its destination."""

    relative_path: str
    purpose: str


CAMPAIGN_ASSETS = (
    CampaignAsset("captions/instagram.md", "Instagram launch caption"),
    CampaignAsset("captions/facebook.md", "Facebook launch post"),
    CampaignAsset("captions/tiktok.md", "TikTok video caption"),
    CampaignAsset("captions/x.md", "X launch post"),
    CampaignAsset("radio/pitch.md", "radio presenter and DJ pitch"),
    CampaignAsset("playlist/pitch.md", "playlist curator pitch"),
    CampaignAsset("press/press-release.md", "music press release"),
    CampaignAsset("schedule/content-calendar.md", "four-week content calendar"),
)


class CampaignGeneratorService:
    """Generate campaign assets using a configured AI provider."""

    def __init__(self, project: Project, provider: AIProvider) -> None:
        self.project = project
        self.provider = provider

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
            response = self.provider.generate(
                self._build_prompt(manifest, asset),
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

    def _build_prompt(self, manifest: dict[str, object], asset: CampaignAsset) -> str:
        hashtags = manifest.get("hashtags") or []
        platforms = manifest.get("platforms") or []
        goals = manifest.get("goals") or {}

        return f"""Create a {asset.purpose} for this music campaign.

Campaign: {manifest["name"]}
Artist: {manifest["artist"]}
Genre: {self.project.genre or "Not specified"}
Release date: {manifest.get("release_date") or "Not specified"}
Spotify: {manifest.get("spotify") or "Not specified"}
Smart link: {manifest.get("smart_link") or "Not specified"}
Hashtags: {hashtags}
Platforms: {platforms}
Goals: {goals}

Requirements:
- Keep facts grounded in the supplied campaign details.
- Do not invent achievements, endorsements, radio plays, or streaming figures.
- Use a confident, authentic artist voice.
- Include a clear call to action where appropriate.
- Return only the finished Markdown content.
"""
