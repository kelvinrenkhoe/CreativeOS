"""Safe campaign milestone inspection and mutation."""

from datetime import date
from pathlib import Path

import yaml

from models.campaign_context import CampaignContext, CampaignContextError
from services.campaign_context import CampaignContextLoadError, CampaignContextService

CAMPAIGN_FILENAME = "campaign.yaml"


class CampaignMilestoneServiceError(Exception):
    """Raised when campaign milestones cannot be safely updated."""


class CampaignMilestoneService:
    """Manage named milestone dates for one organization project campaign."""

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
        try:
            self.campaign = self.campaign_service.load(campaign_id)
            self.campaign_root = self.campaign_service.campaign_path(campaign_id)
        except CampaignContextLoadError as exc:
            raise CampaignMilestoneServiceError(str(exc)) from exc
        self.config_path = self.campaign_root / CAMPAIGN_FILENAME

    def list(self) -> tuple[tuple[str, date], ...]:
        """Return milestone dates in stable name order."""
        campaign = self._load_campaign()
        return tuple(sorted(campaign.milestones, key=lambda item: item[0]))

    def set(self, name: str, value: str | date) -> CampaignContext:
        """Create or update one campaign milestone."""
        milestone_name = self._normalize_name(name)
        raw = self._load_raw()
        milestones = raw.get("milestones", {})
        if milestones is None:
            milestones = {}
        if not isinstance(milestones, dict):
            raise CampaignMilestoneServiceError("campaign.milestones must be a mapping")

        milestones = {
            self._normalize_name(str(key)): self._serialize_date(milestone_value)
            for key, milestone_value in milestones.items()
        }
        milestones[milestone_name] = self._serialize_date(value)
        raw["milestones"] = milestones
        campaign = self._validate(raw)
        self._write(raw)
        self.campaign = campaign
        return campaign

    def remove(self, name: str) -> CampaignContext:
        """Remove one existing campaign milestone."""
        milestone_name = self._normalize_name(name)
        raw = self._load_raw()
        milestones = raw.get("milestones", {})
        if not isinstance(milestones, dict):
            raise CampaignMilestoneServiceError("campaign.milestones must be a mapping")

        milestones = {
            self._normalize_name(str(key)): self._serialize_date(milestone_value)
            for key, milestone_value in milestones.items()
        }
        if milestone_name not in milestones:
            raise CampaignMilestoneServiceError(f"unknown campaign milestone {milestone_name!r}")

        del milestones[milestone_name]
        if milestones:
            raw["milestones"] = milestones
        else:
            raw.pop("milestones", None)

        campaign = self._validate(raw)
        self._write(raw)
        self.campaign = campaign
        return campaign

    def _load_campaign(self) -> CampaignContext:
        return self._validate(self._load_raw())

    def _load_raw(self) -> dict[str, object]:
        try:
            raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise CampaignMilestoneServiceError(
                f"unable to read {self.config_path}: {exc}"
            ) from exc
        except yaml.YAMLError as exc:
            raise CampaignMilestoneServiceError(
                f"invalid YAML in {self.config_path}: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise CampaignMilestoneServiceError("campaign configuration must be a mapping")
        return dict(raw)

    @staticmethod
    def _validate(raw: dict[str, object]) -> CampaignContext:
        try:
            return CampaignContext.from_dict(raw)
        except CampaignContextError as exc:
            raise CampaignMilestoneServiceError(str(exc)) from exc

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip().casefold()
        try:
            CampaignContext(
                campaign_id="validation",
                name="validation",
                milestones=((normalized, date(2000, 1, 1)),),
            )
        except CampaignContextError as exc:
            raise CampaignMilestoneServiceError(str(exc)) from exc
        return normalized

    @staticmethod
    def _serialize_date(value: object) -> str:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return value
        raise CampaignMilestoneServiceError("campaign milestone dates must be ISO dates")

    def _write(self, raw: dict[str, object]) -> None:
        temporary_path = self.config_path.with_suffix(".yaml.tmp")
        try:
            temporary_path.write_text(
                yaml.safe_dump(raw, sort_keys=False),
                encoding="utf-8",
            )
            temporary_path.replace(self.config_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise CampaignMilestoneServiceError(
                f"unable to write {self.config_path}: {exc}"
            ) from exc
