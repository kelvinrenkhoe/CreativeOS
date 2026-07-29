from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from services.publication_reconciliation import (
    ObservedPublication,
    PublicationReconciliationService,
)
from services.publishing import PublicationRequest
from services.runtime_checkpoints import RuntimeCheckpoint

STARTED = datetime(2026, 7, 29, 12, tzinfo=UTC)


@dataclass
class FakeEvidenceSource:
    observations: tuple[ObservedPublication, ...]
    calls: list[datetime]

    @property
    def platform(self) -> str:
        return "instagram"

    def recent_publications(
        self,
        *,
        since: datetime,
    ) -> tuple[ObservedPublication, ...]:
        self.calls.append(since)
        return self.observations


def checkpoint() -> RuntimeCheckpoint:
    return RuntimeCheckpoint(
        checkpoint_id="runtime-publication-123",
        campaign_id="no-lose-guard-campaign",
        action_key="publication:no-lose-guard-teaser",
        status="uncertain",
        started_at=STARTED,
    )


def request() -> PublicationRequest:
    return PublicationRequest(
        asset_id="no-lose-guard-teaser",
        platform="Instagram",
        content="No Lose Guard. September 1.",
        media=("https://cdn.example.test/no-lose-guard.mp4",),
    )


def observation(
    external_id: str = "media-456",
    *,
    content: str = "No Lose Guard. September 1.",
    media: tuple[str, ...] = ("https://cdn.example.test/no-lose-guard.mp4",),
    published_at: datetime = STARTED + timedelta(minutes=1),
) -> ObservedPublication:
    return ObservedPublication(
        platform="instagram",
        external_id=external_id,
        content=content,
        media=media,
        published_at=published_at,
        url=f"https://instagram.example.test/p/{external_id}",
    )


def test_reports_one_exact_provider_match_for_human_review() -> None:
    source = FakeEvidenceSource((observation(),), [])

    result = PublicationReconciliationService().reconcile(
        checkpoint(),
        request(),
        source,
    )

    assert source.calls == [STARTED]
    assert result.status == "found"
    assert result.requires_human_review is True
    assert result.candidates[0].external_id == "media-456"


def test_does_not_assume_success_when_provider_has_no_match() -> None:
    source = FakeEvidenceSource(
        (observation(content="A different Instagram post"),),
        [],
    )

    result = PublicationReconciliationService().reconcile(
        checkpoint(),
        request(),
        source,
    )

    assert result.status == "not-found"
    assert result.candidates == ()
    assert result.requires_human_review is True


def test_reports_multiple_exact_matches_as_ambiguous() -> None:
    source = FakeEvidenceSource(
        (observation("media-456"), observation("media-789")),
        [],
    )

    result = PublicationReconciliationService().reconcile(
        checkpoint(),
        request(),
        source,
    )

    assert result.status == "ambiguous"
    assert tuple(item.external_id for item in result.candidates) == (
        "media-456",
        "media-789",
    )


def test_ignores_matching_publication_that_predates_the_attempt() -> None:
    source = FakeEvidenceSource(
        (observation(published_at=STARTED - timedelta(seconds=1)),),
        [],
    )

    result = PublicationReconciliationService().reconcile(
        checkpoint(),
        request(),
        source,
    )

    assert result.status == "not-found"


def test_rejects_non_uncertain_or_non_publication_checkpoints() -> None:
    service = PublicationReconciliationService()
    source = FakeEvidenceSource((), [])

    with pytest.raises(ValueError, match="uncertain checkpoint"):
        service.reconcile(
            RuntimeCheckpoint(
                checkpoint_id="runtime-completed",
                campaign_id="campaign-1",
                action_key="publication:asset-1",
                status="completed",
                started_at=STARTED,
                completed_at=STARTED,
                result_action="published",
                resulting_stage="published",
            ),
            request(),
            source,
        )
    with pytest.raises(ValueError, match="not an uncertain publication"):
        service.reconcile(
            RuntimeCheckpoint(
                checkpoint_id="runtime-execution",
                campaign_id="campaign-1",
                action_key="execution:request-1",
                status="uncertain",
                started_at=STARTED,
            ),
            request(),
            source,
        )


def test_rejects_wrong_provider_and_malformed_evidence() -> None:
    service = PublicationReconciliationService()

    with pytest.raises(ValueError, match="does not support"):
        service.reconcile(
            checkpoint(),
            request(),
            type(
                "FacebookEvidenceSource",
                (),
                {
                    "platform": "facebook",
                    "recent_publications": lambda self, *, since: (),
                },
            )(),
        )
    with pytest.raises(ValueError, match="duplicate external IDs"):
        service.reconcile(
            checkpoint(),
            request(),
            FakeEvidenceSource((observation(), observation()), []),
        )
