from dataclasses import dataclass

from utils.leveling import level_from_xp


CASES_PER_LEVEL = 1


@dataclass(frozen=True)
class ProgressionDelta:
    old_xp: int
    new_xp: int
    old_level: int
    new_level: int
    levels_gained: int
    cases_gained: int


def calculate_progression(
    old_xp: int,
    xp_gain: int,
) -> ProgressionDelta:
    """
    Единое правило прогрессии LOST EDEN.

    XP никогда не уменьшается через обычное начисление.
    За каждый полученный уровень выдаётся один EDEN CASE.
    """

    if old_xp < 0:
        raise ValueError("Текущий XP не может быть отрицательным")

    if xp_gain < 0:
        raise ValueError("Начисление XP не может быть отрицательным")

    new_xp = old_xp + xp_gain

    old_level = level_from_xp(old_xp)
    new_level = level_from_xp(new_xp)

    levels_gained = max(
        0,
        new_level - old_level,
    )

    return ProgressionDelta(
        old_xp=old_xp,
        new_xp=new_xp,
        old_level=old_level,
        new_level=new_level,
        levels_gained=levels_gained,
        cases_gained=levels_gained * CASES_PER_LEVEL,
    )
