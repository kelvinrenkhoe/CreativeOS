from datetime import date

import pytest

from models.domain_pack import DomainPack
from models.planning_profile import PlanningProfile, PlanningProfileError


def test_planning_profile_resolves_domain_owned_offsets() -> None:
    profile = PlanningProfile.from_dict(
        {
            "anchor": "event_date",
            "start_offset_days": -14,
            "end_offset_days": 2,
            "milestones": {
                "announcement": -14,
                "registration_close": -1,
                "event": 0,
                "follow_up": 2,
            },
        }
    )

    start, end, milestones = profile.resolve(date(2026, 10, 18))

    assert start == date(2026, 10, 4)
    assert end == date(2026, 10, 20)
    assert dict(milestones) == {
        "announcement": date(2026, 10, 4),
        "registration_close": date(2026, 10, 17),
        "event": date(2026, 10, 18),
        "follow_up": date(2026, 10, 20),
    }


def test_domain_pack_can_define_non_music_planning_semantics() -> None:
    pack = DomainPack.from_dict(
        {
            "id": "product-launch",
            "name": "Product Launch",
            "templates": [],
            "planning": {
                "anchor": "launch_date",
                "start_offset_days": -30,
                "end_offset_days": 14,
                "milestones": {"campaign_start": -30, "launch": 0},
            },
        }
    )

    assert pack.planning_profile is not None
    assert pack.planning_profile.anchor_name == "launch_date"


def test_planning_profile_rejects_invalid_window() -> None:
    with pytest.raises(PlanningProfileError, match="cannot be after"):
        PlanningProfile.from_dict(
            {
                "anchor": "event_date",
                "start_offset_days": 5,
                "end_offset_days": -2,
                "milestones": {},
            }
        )
