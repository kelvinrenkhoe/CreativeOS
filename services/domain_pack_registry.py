"""Repository-backed registry for generic CreativeOS domain packs."""

from pathlib import Path

import yaml

from models.domain_pack import DomainPack, DomainPackError
from models.execution_template import ExecutionTemplate, ExecutionTemplateError

DOMAIN_PACKS_DIRECTORY = Path("templates") / "domain-packs"
EXECUTION_TEMPLATES_DIRECTORY = Path("templates") / "execution"


class DomainPackRegistryError(Exception):
    """Raised when domain packs cannot be safely loaded or resolved."""


class DomainPackRegistry:
    """Discover domain packs and validate their execution-template references."""

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.packs_root = (self.repository_root / DOMAIN_PACKS_DIRECTORY).resolve()
        self.templates_root = (self.repository_root / EXECUTION_TEMPLATES_DIRECTORY).resolve()

    def list(self) -> tuple[DomainPack, ...]:
        """Return valid domain packs in stable identifier order."""
        if not self.packs_root.is_dir():
            return ()
        return tuple(
            self._load_path(path, expected_id=path.stem)
            for path in sorted(self.packs_root.glob("*.yaml"))
            if path.is_file()
        )

    def load(self, pack_id: str) -> DomainPack:
        """Load one domain pack by path-safe identifier."""
        try:
            normalized = DomainPack(
                pack_id=pack_id,
                name="validation-placeholder",
            ).pack_id
        except DomainPackError as exc:
            raise DomainPackRegistryError(str(exc)) from exc

        path = (self.packs_root / f"{normalized}.yaml").resolve()
        if path.parent != self.packs_root:
            raise DomainPackRegistryError("domain pack path escaped registry directory")
        if not path.is_file():
            raise DomainPackRegistryError(f"unknown domain pack {normalized!r}")
        return self._load_path(path, expected_id=normalized)

    def default_template_id(self, pack_id: str) -> str:
        """Resolve a pack's explicitly declared default execution template."""
        pack = self.load(pack_id)
        if pack.default_template_id is None:
            raise DomainPackRegistryError(f"domain pack {pack.pack_id!r} has no default template")
        return pack.default_template_id

    def _load_path(self, path: Path, *, expected_id: str) -> DomainPack:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            pack = DomainPack.from_dict(raw)
        except OSError as exc:
            raise DomainPackRegistryError(f"unable to read {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise DomainPackRegistryError(f"invalid YAML in {path}: {exc}") from exc
        except DomainPackError as exc:
            raise DomainPackRegistryError(str(exc)) from exc

        if pack.pack_id != expected_id:
            raise DomainPackRegistryError(
                f"domain pack id {pack.pack_id!r} does not match filename {expected_id!r}"
            )
        self._validate_templates(pack)
        return pack

    def _validate_templates(self, pack: DomainPack) -> None:
        for template_id in pack.template_ids:
            path = (self.templates_root / f"{template_id}.yaml").resolve()
            if path.parent != self.templates_root or not path.is_file():
                raise DomainPackRegistryError(
                    f"domain pack {pack.pack_id!r} references unknown template {template_id!r}"
                )
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                template = ExecutionTemplate.from_dict(raw)
            except (OSError, yaml.YAMLError, ExecutionTemplateError) as exc:
                raise DomainPackRegistryError(
                    f"domain pack {pack.pack_id!r} references invalid template "
                    f"{template_id!r}: {exc}"
                ) from exc
            if template.template_id != template_id:
                raise DomainPackRegistryError(
                    f"template id {template.template_id!r} does not match filename {template_id!r}"
                )
