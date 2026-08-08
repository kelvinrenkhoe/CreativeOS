from models.content_item import ContentItem
from models.creative_brief import ContentCreativeBrief
from services.content_inventory_inspection import inspect_content_items


def make_item(
    content_id: str,
    *,
    role: str | None,
    content_format: str | None,
    channel: str | None,
    call_to_action: str,
) -> ContentItem:
    return ContentItem(
        content_id=content_id,
        title=content_id.replace("-", " ").title(),
        content_role=role,
        content_format=content_format,
        channel=channel,
        brief=ContentCreativeBrief(
            objective="Build campaign momentum",
            audience="Campaign audience",
            key_message="Communicate the campaign clearly",
            call_to_action=call_to_action,
        ),
    )


def test_inspection_summarizes_campaign_content_coverage() -> None:
    report = inspect_content_items(
        (
            make_item(
                "awareness-video",
                role="awareness",
                content_format="short-video",
                channel="instagram",
                call_to_action="Learn more",
            ),
            make_item(
                "customer-proof",
                role="social-proof",
                content_format="static-image",
                channel="linkedin",
                call_to_action="Learn more",
            ),
        )
    )

    assert report.total_items == 2
    assert report.roles == (("awareness", 1), ("social-proof", 1))
    assert report.formats == (("short-video", 1), ("static-image", 1))
    assert report.channels == (("instagram", 1), ("linkedin", 1))
    assert report.complete_metadata is True
    assert report.repeated_groups == ()


def test_inspection_identifies_missing_content_metadata() -> None:
    report = inspect_content_items(
        (
            make_item(
                "event-reminder",
                role=None,
                content_format=None,
                channel=None,
                call_to_action="",
            ),
        )
    )

    assert report.complete_metadata is False
    assert report.missing_role_ids == ("event-reminder",)
    assert report.missing_format_ids == ("event-reminder",)
    assert report.missing_channel_ids == ("event-reminder",)
    assert report.missing_call_to_action_ids == ("event-reminder",)


def test_inspection_flags_repeated_content_signatures() -> None:
    report = inspect_content_items(
        (
            make_item(
                "launch-one",
                role="launch",
                content_format="short-video",
                channel="social",
                call_to_action="Register now",
            ),
            make_item(
                "launch-two",
                role="launch",
                content_format="short-video",
                channel="social",
                call_to_action="REGISTER NOW",
            ),
            make_item(
                "follow-up",
                role="follow-up",
                content_format="carousel",
                channel="social",
                call_to_action="Read more",
            ),
        )
    )

    assert len(report.repeated_groups) == 1
    repeated = report.repeated_groups[0]
    assert repeated.content_ids == ("launch-one", "launch-two")
    assert repeated.content_role == "launch"
    assert repeated.content_format == "short-video"
    assert repeated.channel == "social"
    assert repeated.call_to_action == "register now"


def test_inspection_handles_partial_signatures_deterministically() -> None:
    report = inspect_content_items(
        (
            make_item(
                "missing-one",
                role=None,
                content_format="short-video",
                channel=None,
                call_to_action="",
            ),
            make_item(
                "missing-two",
                role=None,
                content_format="short-video",
                channel=None,
                call_to_action="",
            ),
        )
    )

    assert report.repeated_groups[0].content_ids == ("missing-one", "missing-two")
