"""
Project service for CreativeOS.

Provides a clean interface to the project configuration.
"""

from typing import Any

from core.config import load_config


class Project:
    """Represents a CreativeOS workspace."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = load_config()

    @property
    def name(self) -> str:
        return self._config["project"]["name"]

    @property
    def version(self) -> str:
        return self._config["project"]["version"]

    @property
    def artist(self) -> str:
        return self._config["artist"]["name"]

    @property
    def genre(self) -> str:
        return self._config["artist"]["genre"]

    @property
    def current_song(self) -> str:
        return self._config["songs"]["current"]

    @property
    def upcoming_song(self) -> str:
        return self._config["songs"]["upcoming"]

    @property
    def active_campaigns(self) -> list[str]:
        return self._config["campaigns"]["active"]
