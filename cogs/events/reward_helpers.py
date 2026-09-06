import discord

from config.economy import (
    CURRENCY_SYMBOL,
    EVENT_REWARD_PRESET_NAMES,
    EVENT_REWARD_PRESETS,
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
            f"{amount} {CURRENCY_SYMBOL}"
        )

    if kind == "xp":
        return f"{amount} XP"

    return f"{amount} EDEN CASE"


def format_reward_bundle(
    rewards: dict[str, int],
) -> str:
    parts = [
        format_reward(kind, amount)
        for kind, amount in rewards.items()
        if amount > 0
    ]

    return " · ".join(parts) or "Без награды"


def format_event_reward_preset(
    preset_key: str | None,
) -> str:
    key = preset_key or "standard"
    rewards = EVENT_REWARD_PRESETS.get(key)

    if rewards is None:
        return "Неизвестная награда"

    name = EVENT_REWARD_PRESET_NAMES.get(
        key,
        key.upper(),
    )

    return (
        f"{name}\n"
        f"{format_reward_bundle(rewards)}"
    )


async def process_xp_rewards(
    guild: discord.Guild,
    results,
) -> None:
    xp_results = [
        result
        for result in results
        if (
            result.status == "granted"
            and result.reward_kind == "xp"
        )
    ]

    for result in xp_results:
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
