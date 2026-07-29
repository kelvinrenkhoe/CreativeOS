"""Build one deterministic inbox for every explicit human campaign decision."""

from dataclasses import dataclass

from services.campaign_orchestration import CampaignRun
from services.provider_execution import ExecutionRequest
from services.publishing import PublicationRequest
from services.recommendation_feedback import RecommendationSet
from services.runtime_checkpoints import RuntimeCheckpoint


@dataclass(frozen=True, slots=True)
class PendingPublication:
    """A publication request associated with its campaign."""

    campaign_id: str
    request: PublicationRequest


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """One stable, human-reviewable decision without side effects."""

    review_id: str
    campaign_id: str
    kind: str
    subject_id: str
    title: str
    detail: str
    priority: str
    allowed_decisions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewInbox:
    """Deterministically ordered pending review work."""

    items: tuple[ReviewItem, ...]

    @property
    def requires_review(self) -> bool:
        """Return whether a human decision is still required."""
        return bool(self.items)


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """An attributable decision for one exact inbox item."""

    review_id: str
    decision: str
    decided_by: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewOutcome:
    """Resolved and pending inbox work after validating human decisions."""

    decided: tuple[tuple[ReviewItem, ReviewDecision], ...]
    pending: tuple[ReviewItem, ...]


class HumanReviewInboxService:
    """Aggregate existing human gates without applying their decisions."""

    _KINDS = {
        "asset-approval": ("approve", "reject"),
        "publication-approval": ("approve", "reject"),
        "uncertain-action": ("confirm-completed", "confirm-not-completed"),
        "strategy-recommendation": ("accept", "reject"),
    }
    _PRIORITY = {"urgent": 0, "high": 1, "normal": 2}

    def build(
        self,
        runs: tuple[CampaignRun, ...],
        execution_requests: tuple[ExecutionRequest, ...] = (),
        publications: tuple[PendingPublication, ...] = (),
        checkpoints: tuple[RuntimeCheckpoint, ...] = (),
        recommendation_sets: tuple[RecommendationSet, ...] = (),
    ) -> ReviewInbox:
        """Return pending review work from existing provider-neutral models."""
        campaigns = self._campaigns(runs)
        items = [
            *self._execution_items(campaigns, execution_requests),
            *self._publication_items(campaigns, publications),
            *self._checkpoint_items(campaigns, checkpoints),
            *self._recommendation_items(campaigns, recommendation_sets),
        ]
        review_ids = tuple(item.review_id for item in items)
        if len(review_ids) != len(set(review_ids)):
            raise ValueError("review IDs must be unique")
        return ReviewInbox(
            items=tuple(
                sorted(
                    items,
                    key=lambda item: (
                        self._PRIORITY[item.priority],
                        item.campaign_id,
                        item.kind,
                        item.subject_id,
                    ),
                )
            )
        )

    def review(
        self,
        inbox: ReviewInbox,
        decisions: tuple[ReviewDecision, ...],
    ) -> ReviewOutcome:
        """Validate decisions while leaving every source model unchanged."""
        by_id = {item.review_id: item for item in inbox.items}
        normalized: dict[str, ReviewDecision] = {}
        for decision in decisions:
            review_id = self._required(decision.review_id, "review_id")
            item = by_id.get(review_id)
            if item is None:
                raise ValueError(f"unknown review_id: {review_id}")
            if review_id in normalized:
                raise ValueError(f"duplicate decision for review_id: {review_id}")
            value = self._required(decision.decision, "decision").casefold()
            if value not in item.allowed_decisions:
                raise ValueError(
                    f"decision for {item.kind} must be one of: {', '.join(item.allowed_decisions)}"
                )
            reason = self._optional(decision.reason)
            if value in {"reject", "confirm-not-completed"} and reason is None:
                raise ValueError(f"{value} decision requires a reason")
            normalized[review_id] = ReviewDecision(
                review_id=review_id,
                decision=value,
                decided_by=self._required(decision.decided_by, "decided_by"),
                reason=reason,
            )

        return ReviewOutcome(
            decided=tuple(
                (item, normalized[item.review_id])
                for item in inbox.items
                if item.review_id in normalized
            ),
            pending=tuple(item for item in inbox.items if item.review_id not in normalized),
        )

    def _execution_items(
        self,
        campaigns: dict[str, CampaignRun],
        requests: tuple[ExecutionRequest, ...],
    ) -> list[ReviewItem]:
        work_to_campaign = {run.work_id: campaign_id for campaign_id, run in campaigns.items()}
        if len(work_to_campaign) != len(campaigns):
            raise ValueError("campaign work IDs must be unique")
        items = []
        for request in requests:
            request_id = self._required(request.request_id, "request_id")
            work_id = self._required(request.work_id, "work_id")
            campaign_id = work_to_campaign.get(work_id)
            if campaign_id is None:
                raise ValueError(f"execution request has unknown work_id: {work_id}")
            asset_id = self._required(request.asset_id, "asset_id")
            media_type = self._required(request.media_type, "media_type").casefold()
            provider = self._required(request.provider, "provider").casefold()
            items.append(
                self._item(
                    campaign_id,
                    "asset-approval",
                    request_id,
                    f"Approve {media_type} asset",
                    f"{asset_id} is ready for execution by {provider}.",
                    "normal",
                )
            )
        return items

    def _publication_items(
        self,
        campaigns: dict[str, CampaignRun],
        publications: tuple[PendingPublication, ...],
    ) -> list[ReviewItem]:
        items = []
        for pending in publications:
            campaign_id = self._known_campaign(campaigns, pending.campaign_id)
            asset_id = self._required(pending.request.asset_id, "publication asset_id")
            platform = self._required(pending.request.platform, "platform").casefold()
            items.append(
                self._item(
                    campaign_id,
                    "publication-approval",
                    f"{platform}:{asset_id}",
                    f"Approve {platform} publication",
                    f"{asset_id} is ready for human-approved publication.",
                    "high",
                )
            )
        return items

    def _checkpoint_items(
        self,
        campaigns: dict[str, CampaignRun],
        checkpoints: tuple[RuntimeCheckpoint, ...],
    ) -> list[ReviewItem]:
        items = []
        for checkpoint in checkpoints:
            if checkpoint.status != "uncertain":
                continue
            campaign_id = self._known_campaign(campaigns, checkpoint.campaign_id)
            items.append(
                self._item(
                    campaign_id,
                    "uncertain-action",
                    self._required(checkpoint.checkpoint_id, "checkpoint_id"),
                    "Reconcile uncertain runtime action",
                    (
                        f"Confirm the external outcome of "
                        f"{self._required(checkpoint.action_key, 'action_key')}."
                    ),
                    "urgent",
                )
            )
        return items

    def _recommendation_items(
        self,
        campaigns: dict[str, CampaignRun],
        sets: tuple[RecommendationSet, ...],
    ) -> list[ReviewItem]:
        items = []
        for recommendation_set in sets:
            campaign_id = self._known_campaign(campaigns, recommendation_set.campaign_id)
            for recommendation in recommendation_set.recommendations:
                recommendation_id = self._required(recommendation.id, "recommendation_id")
                priority = self._required(recommendation.priority, "priority").casefold()
                if priority not in {"high", "medium"}:
                    raise ValueError(f"unsupported recommendation priority: {priority}")
                items.append(
                    self._item(
                        campaign_id,
                        "strategy-recommendation",
                        recommendation_id,
                        self._required(recommendation.action, "recommendation action"),
                        self._required(recommendation.reason, "recommendation reason"),
                        "high" if priority == "high" else "normal",
                    )
                )
        return items

    def _item(
        self,
        campaign_id: str,
        kind: str,
        subject_id: str,
        title: str,
        detail: str,
        priority: str,
    ) -> ReviewItem:
        subject_id = self._required(subject_id, "subject_id")
        return ReviewItem(
            review_id=f"review:{campaign_id}:{kind}:{subject_id}",
            campaign_id=campaign_id,
            kind=kind,
            subject_id=subject_id,
            title=self._required(title, "title"),
            detail=self._required(detail, "detail"),
            priority=priority,
            allowed_decisions=self._KINDS[kind],
        )

    def _campaigns(self, runs: tuple[CampaignRun, ...]) -> dict[str, CampaignRun]:
        campaigns = {self._required(run.campaign_id, "campaign_id"): run for run in runs}
        if len(campaigns) != len(runs):
            raise ValueError("campaign IDs must be unique")
        return campaigns

    def _known_campaign(
        self,
        campaigns: dict[str, CampaignRun],
        campaign_id: str,
    ) -> str:
        campaign_id = self._required(campaign_id, "campaign_id")
        if campaign_id not in campaigns:
            raise ValueError(f"unknown campaign_id: {campaign_id}")
        return campaign_id

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        return normalized

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
