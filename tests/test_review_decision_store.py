"""Tests for durable human-review decision persistence."""

from datetime import UTC, datetime

import pytest

from services.human_review_inbox import ReviewDecision, ReviewInbox, ReviewItem
from services.review_decision_store import (
    JsonReviewDecisionStore,
    ReviewDecisionStateError,
)

DECIDED_AT = datetime(2026, 7, 31, 9, tzinfo=UTC)


def inbox() -> ReviewInbox:
    return ReviewInbox(
        items=(
            ReviewItem(
                review_id="review:campaign-1:publication-approval:instagram:asset-1",
                campaign_id="campaign-1",
                kind="publication-approval",
                subject_id="instagram:asset-1",
                title="Approve Instagram publication",
                detail="asset-1 is ready for human-approved publication.",
                priority="high",
                allowed_decisions=("approve", "reject"),
            ),
        )
    )


def decision(
    value: str = "approve",
    *,
    decided_by: str = "Kelvin",
    reason: str | None = None,
) -> ReviewDecision:
    return ReviewDecision(
        review_id=inbox().items[0].review_id,
        decision=value,
        decided_by=decided_by,
        reason=reason,
    )


def test_persists_attributable_decision_across_store_instances(tmp_path) -> None:
    path = tmp_path / "review-decisions.json"

    stored = JsonReviewDecisionStore(path).record(
        inbox(),
        decision(),
        decided_at=DECIDED_AT,
    )
    restored = JsonReviewDecisionStore(path).load()

    assert restored == (stored,)
    assert stored.campaign_id == "campaign-1"
    assert stored.kind == "publication-approval"
    assert stored.subject_id == "instagram:asset-1"
    assert stored.decision == "approve"
    assert stored.decided_by == "Kelvin"
    assert stored.decided_at == DECIDED_AT


def test_identical_replay_is_idempotent_and_preserves_original_timestamp(tmp_path) -> None:
    store = JsonReviewDecisionStore(tmp_path / "review-decisions.json")
    first = store.record(inbox(), decision(), decided_at=DECIDED_AT)

    replay = store.record(
        inbox(),
        decision(),
        decided_at=datetime(2026, 7, 31, 10, tzinfo=UTC),
    )

    assert replay == first
    assert store.load() == (first,)


@pytest.mark.parametrize(
    "conflict",
    (
        decision("reject", reason="Visual is not ready"),
        decision(decided_by="Another operator"),
    ),
)
def test_conflicting_replay_is_rejected(tmp_path, conflict) -> None:
    store = JsonReviewDecisionStore(tmp_path / "review-decisions.json")
    store.record(inbox(), decision(), decided_at=DECIDED_AT)

    with pytest.raises(ReviewDecisionStateError, match="conflicting decision"):
        store.record(inbox(), conflict, decided_at=DECIDED_AT)


def test_decision_is_validated_by_human_review_service(tmp_path) -> None:
    store = JsonReviewDecisionStore(tmp_path / "review-decisions.json")

    with pytest.raises(ReviewDecisionStateError, match="requires a reason"):
        store.record(inbox(), decision("reject"), decided_at=DECIDED_AT)

    assert store.load() == ()


def test_naive_decision_timestamp_is_rejected(tmp_path) -> None:
    store = JsonReviewDecisionStore(tmp_path / "review-decisions.json")

    with pytest.raises(ReviewDecisionStateError, match="timezone-aware"):
        store.record(
            inbox(),
            decision(),
            decided_at=datetime(2026, 7, 31, 9),
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ('{"version": 99, "decisions": []}\n', "unsupported review decision store version"),
        ('{"version": 1, "decisions": [}\n', "invalid review decision snapshot"),
        (
            '{"version": 1, "decisions": [{"review_id": "review-1"}]}\n',
            "invalid review decision snapshot",
        ),
    ),
)
def test_corrupt_or_unsupported_state_fails_closed(tmp_path, payload, message) -> None:
    path = tmp_path / "review-decisions.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ReviewDecisionStateError, match=message):
        JsonReviewDecisionStore(path).load()


def test_duplicate_review_ids_in_snapshot_fail_closed(tmp_path) -> None:
    path = tmp_path / "review-decisions.json"
    store = JsonReviewDecisionStore(path)
    store.record(inbox(), decision(), decided_at=DECIDED_AT)
    payload = path.read_text(encoding="utf-8")
    encoded = payload.replace(
        '"decisions": [',
        '"decisions": ['
        '{"campaign_id":"campaign-1","decided_at":"2026-07-31T09:00:00+00:00",'
        '"decided_by":"Kelvin","decision":"approve","kind":"publication-approval",'
        '"reason":null,"review_id":"review:campaign-1:publication-approval:instagram:asset-1",'
        '"subject_id":"instagram:asset-1"},',
    )
    path.write_text(encoded, encoding="utf-8")

    with pytest.raises(ReviewDecisionStateError, match="duplicate decision"):
        JsonReviewDecisionStore(path).load()
