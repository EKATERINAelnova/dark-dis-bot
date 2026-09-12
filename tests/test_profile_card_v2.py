from utils.profile_card_v2 import (
    ProfileCardData,
    format_voice_time,
    get_profile_badges,
    verification_value,
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


def test_verified_profile_values():
    data = make_data()
    values = get_profile_badges(data)

    assert values == [
        ("ПРОЙДЕНА", "verification"),
        ("Bloom", "milestone"),
        ("3", "cases"),
    ]


def test_pending_profile_without_milestone():
    data = make_data(
        verification_status="pending",
        milestone_name=None,
        eden_cases=0,
    )

    values = get_profile_badges(data)

    assert values == [
        ("ОЖИДАЕТ", "verification"),
        ("НЕ ОТКРЫТА", "milestone"),
        ("0", "cases"),
    ]


def test_unconfigured_verification_value():
    assert verification_value(
        "unconfigured"
    ) == "НЕ НАСТРОЕНА"


def test_unknown_verification_status_is_pending():
    assert verification_value(
        "something_else"
    ) == "ОЖИДАЕТ"


def test_voice_time_is_localized():
    assert format_voice_time(0) == "0 мин"
    assert format_voice_time(3720) == "1 ч 02 мин"
