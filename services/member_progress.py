from dataclasses import dataclass

from database.member_stats import (
    get_member_rank,
    get_member_stats,
)
from database.models import MemberStats
from services.achievements import (
    ACHIEVEMENTS,
    get_unlocked_achievement_keys,
)
from services.activity_progress import (
    MemberActivityProgress,
    get_member_activity_progress,
)
from services.level_roles import (
    get_current_level_role,
    get_next_level_role,
)
from services.rituals import get_daily_ritual_status
from utils.leveling import (
    level_from_xp,
    xp_to_next_level,
)


@dataclass(frozen=True)
class MemberProgress:
    stats: MemberStats
    activities: MemberActivityProgress
    level: int
    rank: int
    xp_to_next_level: int
    current_milestone: tuple[int, str] | None
    next_milestone: tuple[int, str] | None
    achievements_unlocked: int
    achievements_total: int
    ritual_available: bool
    ritual_remaining_seconds: int


async def get_member_progress(
    guild_id: int,
    user_id: int,
) -> MemberProgress:
    stats = await get_member_stats(
        guild_id=guild_id,
        user_id=user_id,
    )

    level = level_from_xp(stats.xp)

    rank = await get_member_rank(
        guild_id=guild_id,
        user_id=user_id,
    )

    activities = await get_member_activity_progress(
        guild_id=guild_id,
        user_id=user_id,
    )

    unlocked_keys = await get_unlocked_achievement_keys(
        guild_id=guild_id,
        user_id=user_id,
    )

    ritual_status = await get_daily_ritual_status(
        guild_id=guild_id,
        user_id=user_id,
    )

    return MemberProgress(
        stats=stats,
        activities=activities,
        level=level,
        rank=rank,
        xp_to_next_level=xp_to_next_level(stats.xp),
        current_milestone=get_current_level_role(level),
        next_milestone=get_next_level_role(level),
        achievements_unlocked=len(unlocked_keys),
        achievements_total=len(ACHIEVEMENTS),
        ritual_available=ritual_status.available,
        ritual_remaining_seconds=ritual_status.remaining_seconds,
    )
