from config.economy import (
    CURRENCY_SYMBOL,
    EVENT_REWARD_PRESET_NAMES,
)
from services.automatic_activity_rewards import get_event_rewards
from services.reward_processing import process_xp_rewards


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
