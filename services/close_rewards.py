from config.economy import (
    CLOSE_PARTICIPATION_XP,
    CLOSE_WIN_BONUS_CURRENCY,
    CLOSE_WIN_BONUS_XP,
)

from services.activity_rewards import (
    ActivityRewardResult,
    grant_activity_reward,
    reward_activity_participants,
)
from services.close_results import get_close_result
from services.close_teams import get_close_teams


async def reward_close_automatically(
    guild_id: int,
    activity_id: int,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    result = await get_close_result(activity_id)

    if (
        result is None
        or result.status != "confirmed"
    ):
        return []

    reward_results = []

    participation = await reward_activity_participants(
        guild_id=guild_id,
        activity_id=activity_id,
        reward_kind="xp",
        amount=CLOSE_PARTICIPATION_XP,
        actor_id=actor_id,
        reward_prefix="auto:close:participation",
    )

    reward_results.extend(participation)

    teams = await get_close_teams(activity_id)

    winners = (
        teams.team_a
        if result.winner_team == "a"
        else teams.team_b
    )

    for user_id in winners:
        xp_result = await grant_activity_reward(
            guild_id=guild_id,
            activity_id=activity_id,
            user_id=user_id,
            reward_key="auto:close:winner:xp",
            reward_kind="xp",
            amount=CLOSE_WIN_BONUS_XP,
            actor_id=actor_id,
        )

        reward_results.append(xp_result)

        currency_result = await grant_activity_reward(
            guild_id=guild_id,
            activity_id=activity_id,
            user_id=user_id,
            reward_key="auto:close:winner:currency",
            reward_kind="currency",
            amount=CLOSE_WIN_BONUS_CURRENCY,
            actor_id=actor_id,
        )

        reward_results.append(currency_result)

    return reward_results
