"""
Configuration loading for CreativeOS.

This module discovers a CreativeOS workspace and loads its project.yaml file.
"""

from pathlib import Path
from typing import Any

import yaml


CONFIG_RELATIVE_PATH = Path("creativeos-config/project.yaml")


class ConfigurationError(Exception):
    """Raised when CreativeOS configuration cannot be found or loaded."""


def find_workspace(start_path: Path | None = None) -> Path:
    """
    Find the CreativeOS workspace by searching upwards for project.yaml.

    Args:
        start_path: Directory to start searching from. Defaults to current directory.

    Returns:
        Path: Workspace root directory.

    Raises:
        ConfigurationError: If no CreativeOS workspace is found.
    """
    current_path = (start_path or Path.cwd()).resolve()

    if current_path.is_file():
        current_path = current_path.parent

    for path in [current_path, *current_path.parents]:
        config_path = path / CONFIG_RELATIVE_PATH
        if config_path.exists():
            return path

    raise ConfigurationError(
        "CreativeOS workspace not found. "
        "Expected creativeos-config/project.yaml in this directory or a parent directory."
    )


def load_config(start_path: Path | None = None) -> dict[str, Any]:
    """
    Load CreativeOS project configuration from project.yaml.

    Args:
        start_path: Directory to start searching from. Defaults to current directory.

    Returns:
        dict[str, Any]: Parsed YAML configuration.

    Raises:
        ConfigurationError: If config file is missing, empty, or invalid.
    """
    workspace_root = find_workspace(start_path)
    config_path = workspace_root / CONFIG_RELATIVE_PATH

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML configuration: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigurationError("Configuration file is empty or invalid.")

    return config
