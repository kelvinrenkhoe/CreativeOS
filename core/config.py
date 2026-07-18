"""Configuration discovery and loading for CreativeOS workspaces."""

from pathlib import Path

import yaml

from models.config import CreativeOSConfig

CONFIG_FILENAME = "creativeos.yaml"


class ConfigurationError(Exception):
    """Raised when CreativeOS configuration cannot be found or loaded."""


def find_workspace(start_path: Path | None = None) -> Path:
    """Find the nearest CreativeOS workspace by searching parent directories."""
    current_path = (start_path or Path.cwd()).resolve()
    if current_path.is_file():
        current_path = current_path.parent

    for path in (current_path, *current_path.parents):
        if (path / CONFIG_FILENAME).is_file():
            return path

    raise ConfigurationError(
        f"CreativeOS workspace not found. Expected {CONFIG_FILENAME} in this "
        "directory or a parent directory."
    )


def load_config(start_path: Path | None = None) -> CreativeOSConfig:
    """Load and validate the nearest CreativeOS workspace configuration."""
    workspace_root = find_workspace(start_path)
    config_path = workspace_root / CONFIG_FILENAME

    try:
        with config_path.open("r", encoding="utf-8") as file:
            raw_config = yaml.safe_load(file)
    except OSError as exc:
        raise ConfigurationError(f"Unable to read {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML configuration: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigurationError("Configuration file is empty or invalid.")

    try:
        return CreativeOSConfig.from_dict(raw_config)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid CreativeOS configuration: {exc}") from exc
