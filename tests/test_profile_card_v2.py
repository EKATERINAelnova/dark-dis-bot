from utils.profile_card_v2 import (
    ProfileCardData,
    get_profile_badges,
)


def make_data(**overrides) -> ProfileCardData:
    values = {
        "level": 5,
        "rank": 2,
        "currency": 100,
        "messages": 250,
        "voice_seconds": 3600,
        "total_xp": 1000,
        "xp_to_next_level": 500,
        "eden_cases": 3,
        "verification_status": "verified",
        "milestone_name": "Bloom",
    }
    values.update(overrides)
    return ProfileCardData(**values)


def test_verified_profile_badges_include_milestone_and_cases():
    badges = get_profile_badges(make_data())

    assert [text for text, _ in badges] == [
        "VERIFIED",
        "Bloom",
        "CASES · 3",
    ]


def test_pending_profile_without_milestone_stays_compact():
    badges = get_profile_badges(
        make_data(
            verification_status="pending",
            milestone_name=None,
            eden_cases=0,
        )
    )

    assert [text for text, _ in badges] == [
        "PENDING",
        "CASES · 0",
    ]


def test_unconfigured_verification_has_separate_badge():
    badges = get_profile_badges(
        make_data(
            verification_status="unconfigured",
        )
    )

    assert badges[0][0] == "VERIFICATION OFF"
