import logging

import discord

from database.member_stats import get_member_stats
from services.achievements import check_achievements
from services.level_roles import sync_level_role
from utils.leveling import level_from_xp


logger = logging.getLogger("lost_eden.rewards")


async def process_xp_rewards(
    guild: discord.Guild,
    results,
) -> None:
    """
    Применяет побочные эффекты после выдачи наград:
    достижения и актуальную milestone-роль уровня.

    Роль сверяется с текущим XP из БД. Это важно для retry:
    выплата могла пройти до сбоя, а Discord-роль не успеть обновиться.
    """

    user_ids = {
        result.user_id
        for result in results
    }

    for user_id in user_ids:
        await check_achievements(
            guild_id=guild.id,
            user_id=user_id,
        )

    xp_user_ids = {
        result.user_id
        for result in results
        if (
            result.reward_kind == "xp"
            and result.status in {
                "granted",
                "already_granted",
            }
        )
    }

    for user_id in xp_user_ids:
        member = guild.get_member(
            user_id
        )

        if member is None:
            continue

        stats = await get_member_stats(
            guild_id=guild.id,
            user_id=user_id,
        )

        try:
            await sync_level_role(
                member=member,
                level=level_from_xp(stats.xp),
            )

        except (
            discord.HTTPException,
            RuntimeError,
        ):
            logger.exception(
                "Не удалось синхронизировать level-role | guild=%s | user=%s",
                guild.id,
                user_id,
            )
