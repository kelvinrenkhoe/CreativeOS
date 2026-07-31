"""Tests for deterministic campaign-run collection loading."""

from types import SimpleNamespace

from services.campaign_run_state import JsonCampaignRunStore


def test_load_all_uses_validated_load_in_campaign_id_order(tmp_path, monkeypatch) -> None:
    directory = tmp_path / "campaign-runs"
    directory.mkdir()
    (directory / "z-campaign.json").write_text("{}\n", encoding="utf-8")
    (directory / "a-campaign.json").write_text("{}\n", encoding="utf-8")
    (directory / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    observed = []

    def load(_store, campaign_id):
        observed.append(campaign_id)
        return SimpleNamespace(campaign_id=campaign_id)

    monkeypatch.setattr(JsonCampaignRunStore, "load", load)

    runs = JsonCampaignRunStore(directory).load_all()

    assert tuple(run.campaign_id for run in runs) == (
        "a-campaign",
        "z-campaign",
    )
    assert observed == ["a-campaign", "z-campaign"]


def test_load_all_returns_empty_when_store_is_absent(tmp_path) -> None:
    directory = tmp_path / "missing"

    assert JsonCampaignRunStore(directory).load_all() == ()
    assert not directory.exists()
