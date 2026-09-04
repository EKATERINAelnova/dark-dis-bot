import discord

from config.economy import (
    CURRENCY_SYMBOL,
)

from services.achievements import (
    check_achievements,
)

from services.level_roles import (
    sync_level_role,
)


def format_reward(
    kind: str,
    amount: int,
) -> str:
    if kind == "currency":
        return (
            f"{amount} "
            f"{CURRENCY_SYMBOL}"
        )

    if kind == "xp":
        return f"{amount} XP"

    return f"{amount} EDEN CASE"


async def process_xp_rewards(
    guild: discord.Guild,
    results,
) -> None:
    for result in results:
        await check_achievements(
            guild_id=guild.id,
            user_id=result.user_id,
        )

        if (
            result.cases_gained <= 0
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
        ) as error:
            print(
                f"[LEVEL ROLE] {error}"
            )