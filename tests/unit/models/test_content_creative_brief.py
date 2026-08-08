import pytest

from models.creative_brief import ContentCreativeBrief, CreativeBriefError


def test_content_brief_normalizes_generic_production_intent() -> None:
    brief = ContentCreativeBrief(
        objective="  Build awareness  ",
        audience="New customers",
        key_message="Show the value clearly",
        call_to_action="Learn more",
        production_notes="Use approved brand assets",
        approval_expectations="Marketing lead approval",
    )

    assert brief.objective == "Build awareness"
    assert brief.audience == "New customers"
    assert brief.call_to_action == "Learn more"


def test_content_brief_round_trips_configuration() -> None:
    brief = ContentCreativeBrief.from_dict(
        {
            "objective": "Encourage attendance",
            "audience": "Local community",
            "key_message": "Everyone is welcome",
            "call_to_action": "Register",
            "production_notes": "Include venue details",
        }
    )

    assert brief.to_dict() == {
        "objective": "Encourage attendance",
        "audience": "Local community",
        "key_message": "Everyone is welcome",
        "call_to_action": "Register",
        "production_notes": "Include venue details",
    }


def test_content_brief_requires_core_intent_fields() -> None:
    with pytest.raises(CreativeBriefError, match="objective must be a non-empty string"):
        ContentCreativeBrief(objective=" ", audience="Audience", key_message="Message")


def test_content_brief_rejects_non_string_configuration() -> None:
    with pytest.raises(CreativeBriefError, match="creative_brief.audience must be a string"):
        ContentCreativeBrief.from_dict(
            {"objective": "Awareness", "audience": ["customers"], "key_message": "Message"}
        )
