"""Reconcile uncertain publication attempts from read-only provider evidence."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from services.publishing import PublicationReceipt, PublicationRequest
from services.runtime_checkpoints import RuntimeCheckpoint


@dataclass(frozen=True, slots=True)
class ObservedPublication:
    """One publication returned by a read-only provider lookup."""

    platform: str
    external_id: str
    content: str
    media: tuple[str, ...]
    published_at: datetime
    url: str | None = None


class PublicationEvidenceSource(Protocol):
    """Read-only boundary for provider publication history."""

    @property
    def platform(self) -> str:
        """Return the normalized platform handled by this source."""
        ...

    def recent_publications(
        self,
        *,
        since: datetime,
    ) -> tuple[ObservedPublication, ...]:
        """Return provider observations without creating or changing media."""
        ...


@dataclass(frozen=True, slots=True)
class PublicationReconciliationResult:
    """Human-reviewable evidence for one uncertain publication attempt."""

    checkpoint_id: str
    campaign_id: str
    status: str
    candidates: tuple[PublicationReceipt, ...]
    requires_human_review: bool = True


class PublicationReconciliationService:
    """Compare uncertain work with provider evidence without retrying publication."""

    def reconcile(
        self,
        checkpoint: RuntimeCheckpoint,
        request: PublicationRequest,
        source: PublicationEvidenceSource,
    ) -> PublicationReconciliationResult:
        """Return found, not-found, or ambiguous evidence for human review."""
        self._validate_checkpoint(checkpoint)
        normalized_request = self._request(request)
        platform = self._required(source.platform, "evidence source platform").casefold()
        if platform != normalized_request.platform:
            raise ValueError("evidence source does not support request platform")

        observations = source.recent_publications(since=checkpoint.started_at)
        self._validate_observations(observations, platform)
        matches = tuple(
            observation
            for observation in observations
            if self._matches(normalized_request, observation, checkpoint.started_at)
        )

        if not matches:
            status = "not-found"
        elif len(matches) == 1:
            status = "found"
        else:
            status = "ambiguous"

        return PublicationReconciliationResult(
            checkpoint_id=self._required(checkpoint.checkpoint_id, "checkpoint_id"),
            campaign_id=self._required(checkpoint.campaign_id, "campaign_id"),
            status=status,
            candidates=tuple(
                PublicationReceipt(
                    platform=platform,
                    external_id=observation.external_id,
                    url=observation.url,
                )
                for observation in matches
            ),
        )

    @classmethod
    def _matches(
        cls,
        request: PublicationRequest,
        observation: ObservedPublication,
        started_at: datetime,
    ) -> bool:
        return (
            observation.published_at >= started_at
            and observation.platform.strip().casefold() == request.platform
            and observation.content.strip() == request.content
            and tuple(item.strip() for item in observation.media) == request.media
        )

    @classmethod
    def _validate_checkpoint(cls, checkpoint: RuntimeCheckpoint) -> None:
        cls._required(checkpoint.checkpoint_id, "checkpoint_id")
        cls._required(checkpoint.campaign_id, "campaign_id")
        action_key = cls._required(checkpoint.action_key, "action_key")
        if checkpoint.status != "uncertain":
            raise ValueError("publication reconciliation requires an uncertain checkpoint")
        if not action_key.startswith("publication:"):
            raise ValueError("checkpoint is not an uncertain publication action")
        cls._timestamp(checkpoint.started_at, "checkpoint started_at")

    @classmethod
    def _request(cls, request: PublicationRequest) -> PublicationRequest:
        return PublicationRequest(
            asset_id=cls._required(request.asset_id, "asset_id"),
            platform=cls._required(request.platform, "platform").casefold(),
            content=cls._required(request.content, "content"),
            media=tuple(cls._required(item, "media item") for item in request.media),
            scheduled_for=request.scheduled_for.strip() if request.scheduled_for else None,
        )

    @classmethod
    def _validate_observations(
        cls,
        observations: tuple[ObservedPublication, ...],
        platform: str,
    ) -> None:
        identities: set[str] = set()
        for observation in observations:
            if observation.platform.strip().casefold() != platform:
                raise ValueError("provider observation platform does not match evidence source")
            external_id = cls._required(observation.external_id, "observation external_id")
            if external_id in identities:
                raise ValueError("provider observations contain duplicate external IDs")
            identities.add(external_id)
            cls._required(observation.content, "observation content")
            for media in observation.media:
                cls._required(media, "observation media item")
            cls._timestamp(observation.published_at, "observation published_at")

    @staticmethod
    def _timestamp(value: datetime, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone")
        return value

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized
