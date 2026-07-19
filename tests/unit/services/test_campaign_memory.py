from services.campaign_memory import CampaignMemory


def test_new_campaign_memory_is_empty() -> None:
    memory = CampaignMemory()

    assert memory.is_empty()
    assert memory.render() == "No campaign assets have been generated yet."


def test_add_records_campaign_asset() -> None:
    memory = CampaignMemory()

    memory.add(
        relative_path="captions/instagram.md",
        purpose="Instagram launch caption",
        content="  Stream the new single now.  ",
    )

    assert not memory.is_empty()
    assert len(memory.entries) == 1
    assert memory.entries[0].relative_path == "captions/instagram.md"
    assert memory.entries[0].purpose == "Instagram launch caption"
    assert memory.entries[0].content == "Stream the new single now."


def test_render_preserves_asset_order() -> None:
    memory = CampaignMemory()

    memory.add(
        relative_path="captions/instagram.md",
        purpose="Instagram launch caption",
        content="Instagram content",
    )
    memory.add(
        relative_path="captions/facebook.md",
        purpose="Facebook launch post",
        content="Facebook content",
    )

    rendered = memory.render()

    assert "## Instagram launch caption" in rendered
    assert "File: captions/instagram.md" in rendered
    assert "Instagram content" in rendered
    assert "## Facebook launch post" in rendered
    assert "File: captions/facebook.md" in rendered
    assert "Facebook content" in rendered
    assert rendered.index("Instagram content") < rendered.index("Facebook content")
