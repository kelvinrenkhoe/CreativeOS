"""Tests for read-only campaign provider execution status."""

from pathlib import Path
from types import SimpleNamespace

from api.campaign_execution_status import CampaignExecutionStatusAPI
from core.project import Project
from services.provider_execution import ExecutionReceipt

CONFIG = """
version: 1
workspace:
  name: Kelvin Rankie Universe
artist:
  name: Kelvin Rankie
repository:
  songs: songs
  campaigns: campaigns
  assets: assets
  knowledge: knowledge
"""


def project(root: Path) -> Project:
    (root / "creativeos.yaml").write_text(CONFIG, encoding="utf-8")
    for directory in ("songs", "campaigns", "assets", "knowledge"):
        (root / directory).mkdir()
    return Project(root)


class Store:
    def __init__(self, value=None, *, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    def load(self, *_args):
        if self.error is not None:
            raise self.error
        return self.value


def request(request_id: str, work_id: str, *, provider: str = "in-memory"):
    return SimpleNamespace(
        request_id=request_id,
        asset_id=f"asset-{request_id}",
        work_id=work_id,
        media_type="image",
        provider=provider,
    )


def job(
    request_id: str,
    work_id: str,
    status: str,
    *,
    receipt: ExecutionReceipt | None = None,
    failure_reason: str | None = None,
):
    return SimpleNamespace(
        request=request(request_id, work_id),
        status=status,
        receipt=receipt,
        failure_reason=failure_reason,
    )


def api(tmp_path: Path, jobs=(), *, run_error=None, queue_error=None):
    run = SimpleNamespace(work_id="work-1")
    queue = SimpleNamespace(queue=SimpleNamespace(jobs=tuple(jobs)))
    return CampaignExecutionStatusAPI(
        project(tmp_path),
        run_store=Store(run, error=run_error),
        queue_store=Store(queue, error=queue_error),
    )


def test_status_returns_completed_receipt_details(tmp_path: Path) -> None:
    receipt = ExecutionReceipt(
        request_id="request-1",
        asset_id="asset-request-1",
        media_type="image",
        provider="in-memory",
        external_id="memory-123",
        outputs=("memory://asset/request-1",),
    )

    result = api(
        tmp_path,
        jobs=(job("request-1", "work-1", "completed", receipt=receipt),),
    ).status("campaign-1")

    assert result.successful
    assert result.work_id == "work-1"
    assert result.total == 1
    assert result.completed == 1
    assert result.pending == 0
    assert result.failed == 0
    assert result.items[0].external_id == "memory-123"
    assert result.items[0].outputs == ("memory://asset/request-1",)


def test_status_counts_pending_and_failed_work(tmp_path: Path) -> None:
    result = api(
        tmp_path,
        jobs=(
            job("request-1", "work-1", "scheduled"),
            job("request-2", "work-1", "failed", failure_reason="provider rejected"),
        ),
    ).status("campaign-1")

    assert result.total == 2
    assert result.pending == 1
    assert result.failed == 1
    assert result.items[1].failure_reason == "provider rejected"


def test_status_ignores_unrelated_work(tmp_path: Path) -> None:
    result = api(
        tmp_path,
        jobs=(
            job("request-1", "other-work", "completed"),
            job("request-2", "work-1", "scheduled"),
        ),
    ).status("campaign-1")

    assert tuple(item.request_id for item in result.items) == ("request-2",)


def test_status_preserves_queue_order(tmp_path: Path) -> None:
    result = api(
        tmp_path,
        jobs=(
            job("request-2", "work-1", "scheduled"),
            job("request-1", "work-1", "scheduled"),
        ),
    ).status("campaign-1")

    assert tuple(item.request_id for item in result.items) == ("request-2", "request-1")


def test_status_warns_when_campaign_has_no_provider_work(tmp_path: Path) -> None:
    result = api(tmp_path).status("campaign-1")

    assert result.successful
    assert result.items == ()
    assert result.warnings == ("no provider execution records found",)


def test_status_structures_run_store_errors(tmp_path: Path) -> None:
    result = api(tmp_path, run_error=ValueError("campaign run missing")).status("campaign-1")

    assert not result.successful
    assert result.errors == ("campaign run missing",)


def test_status_structures_queue_store_errors(tmp_path: Path) -> None:
    result = api(tmp_path, queue_error=ValueError("invalid queue snapshot")).status("campaign-1")

    assert not result.successful
    assert result.errors == ("invalid queue snapshot",)


def test_status_result_counts_remain_consistent(tmp_path: Path) -> None:
    result = api(
        tmp_path,
        jobs=(
            job("request-1", "work-1", "completed"),
            job("request-2", "work-1", "failed"),
            job("request-3", "work-1", "claimed"),
        ),
    ).status("campaign-1")

    assert result.total == result.completed + result.failed + result.pending
