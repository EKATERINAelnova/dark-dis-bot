import pytest

from services.progression import calculate_progression
from utils.leveling import (
    level_from_xp,
    xp_for_level,
    xp_to_next_level,
)


def test_level_boundaries():
    assert xp_for_level(1) == 0
    assert xp_for_level(2) == 100
    assert xp_for_level(3) == 300
    assert xp_for_level(4) == 600

    assert level_from_xp(0) == 1
    assert level_from_xp(99) == 1
    assert level_from_xp(100) == 2
    assert level_from_xp(299) == 2
    assert level_from_xp(300) == 3


def test_xp_to_next_level():
    assert xp_to_next_level(0) == 100
    assert xp_to_next_level(90) == 10
    assert xp_to_next_level(100) == 200


def test_progression_grants_case_for_each_new_level():
    result = calculate_progression(
        old_xp=90,
        xp_gain=610,
    )

    assert result.old_level == 1
    assert result.new_xp == 700
    assert result.new_level == 4
    assert result.levels_gained == 3
    assert result.cases_gained == 3


def test_progression_without_level_up_gives_no_case():
    result = calculate_progression(
        old_xp=10,
        xp_gain=20,
    )

    assert result.new_level == 1
    assert result.cases_gained == 0


def test_progression_rejects_negative_values():
    with pytest.raises(ValueError):
        calculate_progression(
            old_xp=-1,
            xp_gain=1,
        )

    with pytest.raises(ValueError):
        calculate_progression(
            old_xp=0,
            xp_gain=-1,
        )
