from pathlib import Path

import pytest
import yaml

from models.domain_pack import DomainPack, DomainPackError
from services.domain_pack_registry import DomainPackRegistry, DomainPackRegistryError


def _write_template(root: Path, template_id: str = "campaign-template") -> None:
    templates = root / "templates" / "execution"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / f"{template_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": template_id,
                "name": "Campaign Template",
                "actions": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_pack(
    root: Path,
    *,
    pack_id: str = "company-launch",
    template_id: str = "campaign-template",
) -> None:
    packs = root / "templates" / "domain-packs"
    packs.mkdir(parents=True, exist_ok=True)
    (packs / f"{pack_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": pack_id,
                "name": "Company Launch",
                "templates": [template_id],
                "default_template": template_id,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_domain_pack_normalizes_generic_identifiers() -> None:
    pack = DomainPack(
        pack_id="Church Event",
        name="Church Event",
        template_ids=("Event Campaign",),
        default_template_id="Event Campaign",
    )

    assert pack.pack_id == "church-event"
    assert pack.template_ids == ("event-campaign",)
    assert pack.default_template_id == "event-campaign"


def test_domain_pack_requires_default_to_be_declared() -> None:
    with pytest.raises(DomainPackError, match="default_template_id"):
        DomainPack(
            pack_id="book-launch",
            name="Book Launch",
            template_ids=("launch",),
            default_template_id="other",
        )


def test_registry_lists_and_resolves_default_template(tmp_path: Path) -> None:
    _write_template(tmp_path)
    _write_pack(tmp_path)
    registry = DomainPackRegistry(tmp_path)

    packs = registry.list()

    assert tuple(pack.pack_id for pack in packs) == ("company-launch",)
    assert registry.default_template_id("company-launch") == "campaign-template"


def test_registry_rejects_unknown_template_reference(tmp_path: Path) -> None:
    _write_pack(tmp_path, template_id="missing-template")
    registry = DomainPackRegistry(tmp_path)

    with pytest.raises(DomainPackRegistryError, match="unknown template"):
        registry.load("company-launch")


def test_registry_rejects_unsafe_pack_identifier(tmp_path: Path) -> None:
    registry = DomainPackRegistry(tmp_path)

    with pytest.raises(DomainPackRegistryError, match="safe identifier"):
        registry.load("../../company-launch")
