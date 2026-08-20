from config.leveling import LEVEL_BASE_XP

def xp_for_level(level: int) -> int:
    if level <= 1:
        return 0

    return (
        LEVEL_BASE_XP
        * (level - 1)
        * level
        // 2
    )


def level_from_xp(total_xp: int) -> int:
    level = 1

    while total_xp >= xp_for_level(level + 1):
        level += 1

    return level


def xp_to_next_level(total_xp: int) -> int:
    level = level_from_xp(total_xp)
    next_level_xp = xp_for_level(level + 1)

    return next_level_xp - total_xp