"""Filesystem repository for campaign-scoped production assets."""

from pathlib import Path

import yaml

from models.campaign_asset import CampaignAsset, CampaignAssetError


class CampaignAssetRepositoryError(Exception):
    """Raised when campaign asset records cannot be safely stored or loaded."""


class CampaignAssetRepository:
    """Persist immutable campaign asset records within one campaign boundary."""

    def __init__(
        self,
        repository_root: Path,
        organization_id: str,
        project_id: str,
        campaign_id: str,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.assets_root = (
            self.repository_root
            / "organizations"
            / organization_id
            / "projects"
            / project_id
            / "campaigns"
            / campaign_id
            / "assets"
        ).resolve()

    def list(self) -> tuple[CampaignAsset, ...]:
        """Return all stored assets in stable identifier order."""
        if not self.assets_root.is_dir():
            return ()
        return tuple(
            self._load_path(path, expected_id=path.stem)
            for path in sorted(self.assets_root.glob("*.yaml"))
            if path.is_file()
        )

    def load(self, asset_id: str) -> CampaignAsset:
        """Load one asset by path-safe identifier."""
        normalized = self._validated_id(asset_id)
        path = (self.assets_root / f"{normalized}.yaml").resolve()
        if path.parent != self.assets_root:
            raise CampaignAssetRepositoryError("asset path escaped campaign assets directory")
        if not path.is_file():
            raise CampaignAssetRepositoryError(f"unknown campaign asset {normalized!r}")
        return self._load_path(path, expected_id=normalized)

    def save(self, asset: CampaignAsset) -> Path:
        """Create one new campaign asset record without overwriting existing state."""
        path = self._path_for(asset)
        if path.exists():
            raise CampaignAssetRepositoryError(f"campaign asset already exists: {asset.asset_id}")
        self._write(path, asset)
        return path

    def replace(self, asset: CampaignAsset) -> Path:
        """Replace one existing asset record while preserving its stable identifier."""
        path = self._path_for(asset)
        if not path.is_file():
            raise CampaignAssetRepositoryError(f"unknown campaign asset {asset.asset_id!r}")
        current = self._load_path(path, expected_id=asset.asset_id)
        if current.asset_id != asset.asset_id:
            raise CampaignAssetRepositoryError("asset replacement cannot change asset_id")
        self._write(path, asset)
        return path

    def _path_for(self, asset: CampaignAsset) -> Path:
        if not isinstance(asset, CampaignAsset):
            raise CampaignAssetRepositoryError("asset must be a CampaignAsset")
        self.assets_root.mkdir(parents=True, exist_ok=True)
        path = (self.assets_root / f"{asset.asset_id}.yaml").resolve()
        if path.parent != self.assets_root:
            raise CampaignAssetRepositoryError("asset path escaped campaign assets directory")
        return path

    def _write(self, path: Path, asset: CampaignAsset) -> None:
        try:
            path.write_text(
                yaml.safe_dump(asset.to_dict(), sort_keys=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise CampaignAssetRepositoryError(f"unable to write {path}: {exc}") from exc

    def _load_path(self, path: Path, *, expected_id: str) -> CampaignAsset:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            asset = CampaignAsset.from_dict(raw)
        except OSError as exc:
            raise CampaignAssetRepositoryError(f"unable to read {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise CampaignAssetRepositoryError(f"invalid YAML in {path}: {exc}") from exc
        except CampaignAssetError as exc:
            raise CampaignAssetRepositoryError(str(exc)) from exc
        if asset.asset_id != expected_id:
            raise CampaignAssetRepositoryError(
                f"asset id {asset.asset_id!r} does not match filename {expected_id!r}"
            )
        return asset

    @staticmethod
    def _validated_id(asset_id: str) -> str:
        try:
            return CampaignAsset(asset_id, "validation-placeholder", "document").asset_id
        except CampaignAssetError as exc:
            raise CampaignAssetRepositoryError(str(exc)) from exc
