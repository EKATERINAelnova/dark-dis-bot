import logging

import discord

from services.achievements import check_achievements
from services.level_roles import sync_level_role


logger = logging.getLogger("lost_eden.rewards")


async def process_xp_rewards(
    guild: discord.Guild,
    results,
) -> None:
    """
    Применяет побочные эффекты после выдачи наград:
    достижения и актуальную milestone-роль уровня.
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

    for result in results:
        if (
            result.status != "granted"
            or result.reward_kind != "xp"
            or result.cases_gained <= 0
            or result.new_level is None
        ):
            continue

        member = guild.get_member(
            result.user_id
        )

        if member is None:
            continue

        try:
            await sync_level_role(
                member=member,
                level=result.new_level,
            )

        except (
            discord.HTTPException,
            RuntimeError,
        ):
            logger.exception(
                "Не удалось синхронизировать level-role | guild=%s | user=%s",
                guild.id,
                result.user_id,
            )
