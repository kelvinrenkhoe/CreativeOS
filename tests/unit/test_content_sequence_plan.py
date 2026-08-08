import pytest

from models.content_item import ContentItem
from models.creative_brief import ContentCreativeBrief
from services.content_sequence_plan import (
    ContentSequencePlanError,
    build_content_sequence_plan,
)


def _item(
    content_id: str,
    *,
    role: str | None = "story",
    content_format: str | None = "short-video",
    channel: str | None = "social",
    call_to_action: str = "Learn more",
) -> ContentItem:
    return ContentItem(
        content_id=content_id,
        title=content_id,
        brief=ContentCreativeBrief(
            objective="Inform the audience",
            audience="Campaign audience",
            key_message="A useful message",
            call_to_action=call_to_action,
        ),
        content_role=role,
        content_format=content_format,
        channel=channel,
    )


def test_sequence_plan_preserves_supplied_order() -> None:
    plan = build_content_sequence_plan((_item("third"), _item("first"), _item("second")))

    assert tuple(entry.content_id for entry in plan.entries) == ("third", "first", "second")
    assert tuple(entry.position for entry in plan.entries) == (1, 2, 3)


def test_sequence_plan_flags_weak_adjacent_variation() -> None:
    plan = build_content_sequence_plan(
        (
            _item("one"),
            _item("two", call_to_action="Learn more"),
        )
    )

    assert plan.has_weak_variation is True
    assert plan.weak_adjacencies[0].shared_dimensions == (
        "role",
        "format",
        "channel",
        "call-to-action",
    )


def test_sequence_plan_does_not_flag_varied_adjacent_items() -> None:
    plan = build_content_sequence_plan(
        (
            _item("one"),
            _item(
                "two",
                role="social-proof",
                content_format="carousel",
                call_to_action="Register now",
            ),
        )
    )

    assert plan.has_weak_variation is False
    assert plan.adjacency_signals[0].shared_dimensions == ("channel",)


def test_missing_metadata_does_not_count_as_repetition() -> None:
    plan = build_content_sequence_plan(
        (
            _item("one", role=None, content_format=None, channel=None, call_to_action=""),
            _item("two", role=None, content_format=None, channel=None, call_to_action=""),
        )
    )

    assert plan.adjacency_signals[0].shared_dimensions == ()
    assert plan.has_weak_variation is False


def test_sequence_service_rejects_duplicate_ids_before_loading() -> None:
    class Repository:
        def load(self, content_id: str):
            raise AssertionError("repository should not be called")

    from services.content_sequence_plan import ContentSequencePlanService

    service = ContentSequencePlanService(Repository())
    with pytest.raises(ContentSequencePlanError, match="must be unique"):
        service.plan(("one", "one"))
