from models.content_inventory_report import ContentInventoryReport, ContentVariationGroup
from services.content_sequence_recommendation import recommend_from_report


def _report(**overrides) -> ContentInventoryReport:
    values = {
        "total_items": 2,
        "roles": (("awareness", 2),),
        "formats": (("short-video", 2),),
        "channels": (("social", 2),),
        "missing_role_ids": (),
        "missing_format_ids": (),
        "missing_channel_ids": (),
        "missing_call_to_action_ids": (),
        "repeated_groups": (),
    }
    values.update(overrides)
    return ContentInventoryReport(**values)


def test_no_recommendations_for_complete_varied_inventory() -> None:
    report = recommend_from_report(_report())

    assert report.recommendations == ()
    assert not report.has_recommendations


def test_recommends_completing_missing_metadata_first() -> None:
    report = recommend_from_report(
        _report(
            missing_role_ids=("launch-one",),
            missing_call_to_action_ids=("launch-two",),
        )
    )

    assert tuple(item.recommendation_id for item in report.recommendations) == (
        "complete-role",
        "complete-call-to-action",
    )
    assert report.recommendations[0].content_ids == ("launch-one",)


def test_recommends_varying_repeated_content_signature() -> None:
    repeated = ContentVariationGroup(
        content_ids=("post-one", "post-two"),
        content_role="awareness",
        content_format="short-video",
        channel="social",
        call_to_action="register",
    )

    report = recommend_from_report(_report(repeated_groups=(repeated,)))

    recommendation = report.recommendations[0]
    assert recommendation.recommendation_id == "vary-repeated-signature-1"
    assert recommendation.content_ids == ("post-one", "post-two")
    assert "role, format, channel, call-to-action" in recommendation.summary
