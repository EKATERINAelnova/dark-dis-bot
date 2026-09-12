from dataclasses import dataclass

from database.member_stats import get_member_stats
from services.activity_progress import get_member_activity_progress
from services.achievements import (
    ACHIEVEMENTS,
    Achievement,
    check_achievements,
    get_achievement_value,
    get_metric_participations,
    get_unlocked_achievement_keys,
)


@dataclass(frozen=True)
class AchievementProgressItem:
    achievement: Achievement
    value: int
    unlocked: bool
    participations: int = 0


@dataclass(frozen=True)
class AchievementProgressSnapshot:
    items: tuple[AchievementProgressItem, ...]
    unlocked_count: int
    total_count: int
    unlocked_now: tuple[Achievement, ...] = ()


async def get_achievement_progress(
    guild_id: int,
    user_id: int,
    refresh: bool = False,
) -> AchievementProgressSnapshot:
    """
    Возвращает готовый снимок прогресса достижений.

    refresh=True сначала проверяет условия и выдаёт новые
    достижения. Для обычного чтения используется refresh=False,
    чтобы запрос прогресса не имел скрытых побочных эффектов.
    """

    unlocked_now: tuple[Achievement, ...] = ()

    if refresh:
        unlocked_now = tuple(
            await check_achievements(
                guild_id=guild_id,
                user_id=user_id,
            )
        )

    stats = await get_member_stats(
        guild_id=guild_id,
        user_id=user_id,
    )
    activity_progress = await get_member_activity_progress(
        guild_id=guild_id,
        user_id=user_id,
    )
    unlocked_keys = await get_unlocked_achievement_keys(
        guild_id=guild_id,
        user_id=user_id,
    )

    items = []

    for achievement in ACHIEVEMENTS:
        value = get_achievement_value(
            achievement,
            stats,
            activity_progress,
        )

        participations = 0
        if achievement.minimum_participations > 0:
            participations = get_metric_participations(
                achievement,
                activity_progress,
            )

        items.append(
            AchievementProgressItem(
                achievement=achievement,
                value=value,
                unlocked=achievement.key in unlocked_keys,
                participations=participations,
            )
        )

    return AchievementProgressSnapshot(
        items=tuple(items),
        unlocked_count=len(unlocked_keys),
        total_count=len(ACHIEVEMENTS),
        unlocked_now=unlocked_now,
    )
