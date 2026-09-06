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
        return f"{amount} {CURRENCY_SYMBOL}"

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


def encode_custom_event_reward(
    currency: int,
    xp: int,
    cases: int,
) -> str:
    return f"custom:{currency}:{xp}:{cases}"


def get_event_rewards(
    reward_preset: str | None,
) -> dict[str, int]:
    key = reward_preset or "standard"

    if key.startswith("custom:"):
        try:
            _, currency, xp, cases = key.split(":")

            return {
                "currency": int(currency),
                "xp": int(xp),
                "case": int(cases),
            }
        except (ValueError, TypeError):
            return {
                "currency": 0,
                "xp": 0,
                "case": 0,
            }

    return EVENT_REWARD_PRESETS.get(
        key,
        {
            "currency": 0,
            "xp": 0,
            "case": 0,
        },
    )


def format_event_reward_preset(
    preset_key: str | None,
) -> str:
    key = preset_key or "standard"
    rewards = get_event_rewards(key)

    if key.startswith("custom:"):
        name = "CUSTOM EVENT"
    else:
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
