"""Campaign-scoped persistence for executable marketing actions."""

from pathlib import Path

import yaml

from models.action import Action, ActionError
from services.campaign_context import CampaignContextService

ACTIONS_DIRECTORY = "actions"
ACTION_SUFFIX = ".yaml"


class ActionRepositoryError(Exception):
    """Raised when campaign actions cannot be safely persisted or loaded."""


class ActionRepository:
    """Persist actions inside one organization project campaign."""

    def __init__(
        self,
        repository_root: Path,
        organization_id: str,
        project_id: str,
        campaign_id: str,
    ) -> None:
        self.campaign_service = CampaignContextService(
            repository_root,
            organization_id,
            project_id,
        )
        self.campaign = self.campaign_service.load(campaign_id)
        self.campaign_root = self.campaign_service.campaign_path(campaign_id)
        self.actions_root = self.campaign_root / ACTIONS_DIRECTORY

    def list(self) -> tuple[Action, ...]:
        """Return all valid campaign actions in stable identifier order."""
        if not self.actions_root.is_dir():
            return ()

        actions: list[Action] = []
        for config_path in sorted(self.actions_root.glob(f"*{ACTION_SUFFIX}")):
            if config_path.is_file():
                actions.append(self._load_file(config_path, expected_id=config_path.stem))
        return tuple(actions)

    def load(self, action_id: str) -> Action:
        """Load one campaign action by validated identifier."""
        requested = self._validated_id(action_id)
        config_path = self.actions_root / f"{requested}{ACTION_SUFFIX}"
        if not config_path.is_file():
            campaign_id = self.campaign.campaign_id
            raise ActionRepositoryError(
                f"unknown action {requested!r} for campaign {campaign_id!r}"
            )
        return self._load_file(config_path, expected_id=requested)

    def save(self, action: Action) -> Path:
        """Persist an action atomically and return its safe configuration path."""
        config_path = self.action_path(action.action_id)
        self.actions_root.mkdir(parents=True, exist_ok=True)
        temporary_path = config_path.with_suffix(f"{ACTION_SUFFIX}.tmp")

        try:
            temporary_path.write_text(
                yaml.safe_dump(self._to_dict(action), sort_keys=False),
                encoding="utf-8",
            )
            temporary_path.replace(config_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise ActionRepositoryError(f"unable to write {config_path}: {exc}") from exc

        return config_path

    def delete(self, action_id: str) -> None:
        """Delete one existing campaign action."""
        action = self.load(action_id)
        config_path = self.action_path(action.action_id)
        try:
            config_path.unlink()
        except OSError as exc:
            raise ActionRepositoryError(f"unable to delete {config_path}: {exc}") from exc

    def action_path(self, action_id: str) -> Path:
        """Return the safe YAML path for an action identifier."""
        requested = self._validated_id(action_id)
        actions_root = self.actions_root.resolve()
        path = (actions_root / f"{requested}{ACTION_SUFFIX}").resolve()
        if path.parent != actions_root:
            raise ActionRepositoryError("action path escaped the campaign actions directory")
        return path

    @staticmethod
    def _validated_id(action_id: str) -> str:
        try:
            return Action(action_id=action_id, title="validation-placeholder").action_id
        except ActionError as exc:
            raise ActionRepositoryError(str(exc)) from exc

    def _load_file(self, config_path: Path, *, expected_id: str) -> Action:
        try:
            with config_path.open("r", encoding="utf-8") as file:
                raw = yaml.safe_load(file)
        except OSError as exc:
            raise ActionRepositoryError(f"unable to read {config_path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise ActionRepositoryError(f"invalid YAML in {config_path}: {exc}") from exc

        try:
            action = Action.from_dict(raw)
        except ActionError as exc:
            raise ActionRepositoryError(f"invalid action configuration: {exc}") from exc

        if action.action_id != expected_id:
            raise ActionRepositoryError(
                f"action id {action.action_id!r} does not match filename {expected_id!r}"
            )
        return action

    @staticmethod
    def _to_dict(action: Action) -> dict[str, object]:
        data: dict[str, object] = {
            "id": action.action_id,
            "title": action.title,
            "status": action.status,
            "priority": action.priority,
        }
        if action.description:
            data["description"] = action.description
        if action.due_date is not None:
            data["due_date"] = action.due_date.isoformat()
        if action.channel is not None:
            data["channel"] = action.channel
        if action.depends_on:
            data["depends_on"] = list(action.depends_on)
        if action.milestone is not None:
            data["milestone"] = action.milestone
        if action.content_role is not None:
            data["content_role"] = action.content_role
        if action.content_format is not None:
            data["content_format"] = action.content_format
        return data
