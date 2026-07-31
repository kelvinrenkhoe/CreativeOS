"""CLI tests for read-only campaign runtime status."""

from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from cli.campaign import CAMPAIGN_RUNS_PATH, app
from services.campaign_run_state import (
    CampaignRunCorruptedError,
    CampaignRunNotFoundError,
    CampaignRunValidationError,
    CampaignRunVersionError,
    JsonCampaignRunStore,
)

runner = CliRunner()


def persisted_run():
    return SimpleNamespace(
        campaign_id="no-lose-guard-launch",
        work_id="no-lose-guard",
        plan=SimpleNamespace(work_name="No Lose Guard"),
        stage="ready",
        evidence=(
            SimpleNamespace(
                kind="approved-assets",
                reference_id="approval-01",
                recorded_by="Kelvin",
            ),
        ),
        requires_action="Record publication-receipt evidence",
    )


def test_status_displays_persisted_run_without_mutation(tmp_path, monkeypatch) -> None:
    expected_directory = tmp_path / CAMPAIGN_RUNS_PATH
    observed = {}

    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )

    def load(store, campaign_id):
        observed["directory"] = store.directory
        observed["campaign_id"] = campaign_id
        return persisted_run()

    monkeypatch.setattr(JsonCampaignRunStore, "load", load)

    result = runner.invoke(app, ["status", "no-lose-guard-launch"])

    assert result.exit_code == 0
    assert observed == {
        "directory": expected_directory,
        "campaign_id": "no-lose-guard-launch",
    }
    assert "Campaign Runtime Status" in result.stdout
    assert "No Lose Guard" in result.stdout
    assert "ready" in result.stdout
    assert "approved-assets: approval-01 (recorded by Kelvin)" in result.stdout
    assert "Record publication-receipt evidence" in result.stdout
    assert not expected_directory.exists()


@pytest.mark.parametrize(
    ("error", "message"),
    (
        (CampaignRunNotFoundError("Campaign run not found: missing"), "not found"),
        (CampaignRunCorruptedError("Campaign run is corrupt: broken"), "corrupt"),
        (CampaignRunVersionError("Unsupported campaign run version: 999"), "version"),
        (CampaignRunValidationError("Campaign ID mismatch"), "mismatch"),
    ),
)
def test_status_returns_non_zero_for_invalid_runtime_state(
    tmp_path,
    monkeypatch,
    error,
    message,
) -> None:
    monkeypatch.setattr(
        "cli.campaign.Project.discover",
        lambda: SimpleNamespace(root=tmp_path),
    )

    def fail(_store, _campaign_id):
        raise error

    monkeypatch.setattr(JsonCampaignRunStore, "load", fail)

    result = runner.invoke(app, ["status", "broken"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert message.lower() in result.stdout.lower()
