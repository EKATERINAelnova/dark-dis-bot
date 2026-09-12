import time

from config.economy import (
    CLOSE_PARTICIPATION_XP,
    CLOSE_REWARD_DAILY_LIMIT,
    CLOSE_REWARD_WINDOW_SECONDS,
    CLOSE_WIN_BONUS_CURRENCY,
    CLOSE_WIN_BONUS_XP,
)
from database.connection import get_db
from services.activity_rewards import (
    ActivityRewardResult,
    grant_activity_reward,
)
from services.close_results import get_close_result
from services.close_teams import get_close_teams
from services.reward_decisions import (
    get_reward_decision,
    save_reward_decision,
)


CLOSE_REWARD_POLICY = "close:auto"


async def check_close_reward_allowed(
    guild_id: int,
    activity_id: int,
    user_id: int,
) -> str:
    saved_status = await get_reward_decision(
        activity_id=activity_id,
        user_id=user_id,
        policy_key=CLOSE_REWARD_POLICY,
    )

    if saved_status is not None:
        return saved_status

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT confirmed_at
            FROM close_results
            WHERE activity_id = ?
              AND status = 'confirmed'
            """,
            (activity_id,),
        )

        confirmed_row = await cursor.fetchone()
        await cursor.close()

        reference_time = (
            int(confirmed_row[0])
            if (
                confirmed_row is not None
                and confirmed_row[0] is not None
            )
            else int(time.time())
        )

        cursor = await db.execute(
            """
            SELECT COUNT(DISTINCT p.activity_id)
            FROM activity_payouts AS p
            JOIN activities AS a
              ON a.activity_id = p.activity_id
            WHERE a.guild_id = ?
              AND a.type = 'close'
              AND p.user_id = ?
              AND p.activity_id != ?
              AND p.reward_key = 'auto:close:participation:xp'
              AND p.granted_at >= ?
              AND p.granted_at <= ?
            """,
            (
                guild_id,
                user_id,
                activity_id,
                reference_time - CLOSE_REWARD_WINDOW_SECONDS,
                reference_time,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    rewarded_closes = int(row[0] or 0)

    status = (
        "daily_limit"
        if rewarded_closes >= CLOSE_REWARD_DAILY_LIMIT
        else "allowed"
    )

    return await save_reward_decision(
        activity_id=activity_id,
        user_id=user_id,
        policy_key=CLOSE_REWARD_POLICY,
        status=status,
    )


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

    teams = await get_close_teams(activity_id)
    participants = (
        teams.team_a
        + teams.team_b
    )

    winners = set(
        teams.team_a
        if result.winner_team == "a"
        else teams.team_b
    )

    reward_results = []

    for user_id in participants:
        allowed = await check_close_reward_allowed(
            guild_id=guild_id,
            activity_id=activity_id,
            user_id=user_id,
        )

        if allowed != "allowed":
            reward_results.append(
                ActivityRewardResult(
                    status=allowed,
                    user_id=user_id,
                    reward_kind="close",
                    amount=0,
                )
            )
            continue

        participation_result = await grant_activity_reward(
            guild_id=guild_id,
            activity_id=activity_id,
            user_id=user_id,
            reward_key="auto:close:participation:xp",
            reward_kind="xp",
            amount=CLOSE_PARTICIPATION_XP,
            actor_id=actor_id,
        )

        reward_results.append(
            participation_result
        )

        if user_id not in winners:
            continue

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
