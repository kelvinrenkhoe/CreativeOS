"""
Scaffold service for CreativeOS.

Creates files and folders from scaffold definitions.
"""

from pathlib import Path
from typing import Any

import yaml


class ScaffoldError(Exception):
    """Raised when a scaffold cannot be loaded or applied."""


class ScaffoldService:
    """Creates workspace structures from scaffold definitions."""

    def __init__(self, scaffold_root: Path | None = None) -> None:
        self.scaffold_root = scaffold_root or Path(__file__).resolve().parent.parent / "scaffolds"

    def load_structure(self, scaffold_name: str) -> dict[str, Any]:
        structure_path = self.scaffold_root / scaffold_name / "structure.yaml"

        if not structure_path.exists():
            raise ScaffoldError(f"Scaffold not found: {scaffold_name}")

        with structure_path.open("r", encoding="utf-8") as file:
            structure = yaml.safe_load(file)

        if not isinstance(structure, dict):
            raise ScaffoldError(f"Invalid scaffold structure: {scaffold_name}")

        return structure

    def apply(self, scaffold_name: str, target_path: Path) -> None:
        structure = self.load_structure(scaffold_name)

        target_path.mkdir(parents=True, exist_ok=True)

        for folder in structure.get("folders", []):
            (target_path / folder).mkdir(parents=True, exist_ok=True)

        for filename in structure.get("files", []):
            file_path = target_path / filename
            file_path.touch(exist_ok=True)
