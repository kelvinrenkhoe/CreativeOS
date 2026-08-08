from pathlib import Path

import pytest

from models.content_item import ContentItem, ContentItemError
from models.creative_brief import ContentCreativeBrief
from services.content_inventory import ContentInventoryError, ContentInventoryRepository


def make_campaign(tmp_path: Path) -> None:
    project_root = tmp_path / "organizations" / "acme" / "projects" / "launch"
    campaign_root = project_root / "campaigns" / "spring"
    campaign_root.mkdir(parents=True)
    (tmp_path / "organizations" / "acme" / "organization.yaml").write_text(
        "id: acme\nname: Acme\n",
        encoding="utf-8",
    )
    (project_root / "project.yaml").write_text(
        "id: launch\nname: Launch\ntype: initiative\n",
        encoding="utf-8",
    )
    (campaign_root / "campaign.yaml").write_text(
        "id: spring\nname: Spring Campaign\ntype: product-launch\nstatus: draft\n",
        encoding="utf-8",
    )


def sample_item() -> ContentItem:
    return ContentItem(
        content_id="value-demo",
        title="Product value demonstration",
        content_role="education",
        content_format="product-demo",
        channel="linkedin",
        action_id="publish-demo",
        brief=ContentCreativeBrief(
            objective="Explain the product value clearly.",
            audience="Prospective customers",
            key_message="The workflow saves teams time.",
            call_to_action="Book a demo",
        ),
    )


def test_content_item_keeps_brief_separate_from_execution_metadata() -> None:
    item = sample_item()

    assert item.content_role == "education"
    assert item.content_format == "product-demo"
    assert item.channel == "linkedin"
    assert item.action_id == "publish-demo"
    assert item.brief.objective == "Explain the product value clearly."


def test_content_item_rejects_unsafe_identifier() -> None:
    with pytest.raises(ContentItemError, match="path-safe identifier"):
        ContentItem(
            content_id="../../escape",
            title="Unsafe",
            brief=ContentCreativeBrief(
                objective="Objective",
                audience="Audience",
                key_message="Message",
            ),
        )


def test_repository_round_trips_campaign_scoped_content(tmp_path: Path) -> None:
    make_campaign(tmp_path)
    repository = ContentInventoryRepository(tmp_path, "acme", "launch", "spring")

    path = repository.save(sample_item())
    loaded = repository.load("value-demo")

    assert path == (
        tmp_path
        / "organizations"
        / "acme"
        / "projects"
        / "launch"
        / "campaigns"
        / "spring"
        / "content"
        / "value-demo.yaml"
    )
    assert loaded == sample_item()
    assert repository.list() == (sample_item(),)


def test_repository_rejects_content_path_escape(tmp_path: Path) -> None:
    make_campaign(tmp_path)
    repository = ContentInventoryRepository(tmp_path, "acme", "launch", "spring")

    with pytest.raises(ContentInventoryError, match="path-safe identifier"):
        repository.content_path("../../escape")


def test_repository_is_isolated_to_one_campaign(tmp_path: Path) -> None:
    make_campaign(tmp_path)
    other_campaign = (
        tmp_path / "organizations" / "acme" / "projects" / "launch" / "campaigns" / "other"
    )
    other_campaign.mkdir()
    (other_campaign / "campaign.yaml").write_text(
        "id: other\nname: Other Campaign\ntype: awareness\nstatus: draft\n",
        encoding="utf-8",
    )

    spring = ContentInventoryRepository(tmp_path, "acme", "launch", "spring")
    other = ContentInventoryRepository(tmp_path, "acme", "launch", "other")
    spring.save(sample_item())

    assert other.list() == ()
