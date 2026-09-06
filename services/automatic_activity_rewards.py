from config.economy import (
    DUEL_WIN_REWARD,
    EVENT_REWARD_PRESETS,
)

from services.activities import (
    Activity,
)

from services.activity_rewards import (
    ActivityRewardResult,
    grant_activity_reward,
    reward_activity_participants,
)


async def reward_event_automatically(
    activity: Activity,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    preset_key = (
        activity.reward_preset
        or "standard"
    )

    preset = EVENT_REWARD_PRESETS.get(
        preset_key
    )

    if preset is None:
        raise ValueError(
            f"Неизвестный пресет EVENT: {preset_key}"
        )

    results = []

    for reward_kind, amount in preset.items():
        if amount <= 0:
            continue

        reward_results = (
            await reward_activity_participants(
                guild_id=activity.guild_id,
                activity_id=activity.activity_id,
                reward_kind=reward_kind,
                amount=amount,
                actor_id=actor_id,
                reward_prefix=(
                    f"auto:{preset_key}"
                ),
            )
        )

        results.extend(
            reward_results
        )

    return results


async def reward_duel_winner_automatically(
    guild_id: int,
    activity_id: int,
    winner_id: int,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    results = []

    for reward_kind, amount in DUEL_WIN_REWARD.items():
        if amount <= 0:
            continue

        result = await grant_activity_reward(
            guild_id=guild_id,
            activity_id=activity_id,
            user_id=winner_id,
            reward_key=(
                f"auto:winner:{reward_kind}"
            ),
            reward_kind=reward_kind,
            amount=amount,
            actor_id=actor_id,
        )

        results.append(
            result
        )

    return results
