"""Campaign-scoped persistence for planned content inventory."""

from pathlib import Path

import yaml

from models.content_item import ContentItem, ContentItemError
from services.campaign_context import CampaignContextService

CONTENT_DIRECTORY = "content"
CONTENT_SUFFIX = ".yaml"


class ContentInventoryError(Exception):
    """Raised when campaign content inventory cannot be safely handled."""


class ContentInventoryRepository:
    """Persist content items inside one organization project campaign."""

    def __init__(
        self,
        repository_root: Path,
        organization_id: str,
        project_id: str,
        campaign_id: str,
    ) -> None:
        campaign_service = CampaignContextService(repository_root, organization_id, project_id)
        self.campaign = campaign_service.load(campaign_id)
        self.campaign_root = campaign_service.campaign_path(campaign_id)
        self.content_root = self.campaign_root / CONTENT_DIRECTORY

    def list(self) -> tuple[ContentItem, ...]:
        """Return all valid content items in stable identifier order."""
        if not self.content_root.is_dir():
            return ()

        items: list[ContentItem] = []
        for config_path in sorted(self.content_root.glob(f"*{CONTENT_SUFFIX}")):
            if config_path.is_file():
                items.append(self._load_file(config_path, expected_id=config_path.stem))
        return tuple(items)

    def load(self, content_id: str) -> ContentItem:
        """Load one campaign content item by validated identifier."""
        requested = self._validated_id(content_id)
        config_path = self.content_root / f"{requested}{CONTENT_SUFFIX}"
        if not config_path.is_file():
            raise ContentInventoryError(
                f"unknown content item {requested!r} for campaign {self.campaign.campaign_id!r}"
            )
        return self._load_file(config_path, expected_id=requested)

    def save(self, item: ContentItem) -> Path:
        """Persist a content item atomically and return its safe path."""
        config_path = self.content_path(item.content_id)
        self.content_root.mkdir(parents=True, exist_ok=True)
        temporary_path = config_path.with_suffix(f"{CONTENT_SUFFIX}.tmp")
        try:
            temporary_path.write_text(
                yaml.safe_dump(item.to_dict(), sort_keys=False),
                encoding="utf-8",
            )
            temporary_path.replace(config_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise ContentInventoryError(f"unable to write {config_path}: {exc}") from exc
        return config_path

    def delete(self, content_id: str) -> None:
        """Delete one existing content item."""
        item = self.load(content_id)
        config_path = self.content_path(item.content_id)
        try:
            config_path.unlink()
        except OSError as exc:
            raise ContentInventoryError(f"unable to delete {config_path}: {exc}") from exc

    def content_path(self, content_id: str) -> Path:
        """Return the safe YAML path for a content item identifier."""
        requested = self._validated_id(content_id)
        content_root = self.content_root.resolve()
        path = (content_root / f"{requested}{CONTENT_SUFFIX}").resolve()
        if path.parent != content_root:
            raise ContentInventoryError("content path escaped the campaign content directory")
        return path

    @staticmethod
    def _validated_id(content_id: str) -> str:
        try:
            return ContentItem(
                content_id=content_id,
                title="validation-placeholder",
                brief=_validation_brief(),
            ).content_id
        except ContentItemError as exc:
            raise ContentInventoryError(str(exc)) from exc

    def _load_file(self, config_path: Path, *, expected_id: str) -> ContentItem:
        try:
            with config_path.open("r", encoding="utf-8") as file:
                raw = yaml.safe_load(file)
        except OSError as exc:
            raise ContentInventoryError(f"unable to read {config_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ContentInventoryError(f"invalid YAML in {config_path}: {exc}") from exc

        try:
            item = ContentItem.from_dict(raw)
        except ContentItemError as exc:
            raise ContentInventoryError(f"invalid content configuration: {exc}") from exc
        if item.content_id != expected_id:
            raise ContentInventoryError(
                f"content id {item.content_id!r} does not match filename {expected_id!r}"
            )
        return item


def _validation_brief():
    from models.creative_brief import ContentCreativeBrief

    return ContentCreativeBrief(
        objective="validation",
        audience="validation",
        key_message="validation",
    )
