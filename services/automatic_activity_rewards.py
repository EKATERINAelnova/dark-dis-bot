import time

from config.economy import (
    DUEL_MIN_DURATION_SECONDS,
    DUEL_PAIR_REWARD_COOLDOWN_SECONDS,
    DUEL_REWARD_DAILY_LIMIT,
    DUEL_REWARD_WINDOW_SECONDS,
    DUEL_WIN_REWARD,
)

from cogs.events.reward_helpers import (
    get_event_rewards,
)

from database.connection import get_db

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
    rewards = get_event_rewards(
        activity.reward_preset
    )

    results = []

    for reward_kind, amount in rewards.items():
        if amount <= 0:
            continue

        reward_results = (
            await reward_activity_participants(
                guild_id=activity.guild_id,
                activity_id=activity.activity_id,
                reward_kind=reward_kind,
                amount=amount,
                actor_id=actor_id,
                reward_prefix="auto:event",
            )
        )

        results.extend(
            reward_results
        )

    return results


async def check_duel_reward_allowed(
    guild_id: int,
    activity_id: int,
    winner_id: int,
) -> str:
    now = int(time.time())

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT starts_at
            FROM activities
            WHERE guild_id = ?
              AND activity_id = ?
              AND type = 'duel'
            """,
            (
                guild_id,
                activity_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return "not_found"

        starts_at = (
            int(row[0])
            if row[0] is not None
            else None
        )

        if (
            starts_at is None
            or now - starts_at < DUEL_MIN_DURATION_SECONDS
        ):
            return "too_short"

        cursor = await db.execute(
            """
            SELECT COUNT(DISTINCT activity_id)
            FROM activity_payouts
            WHERE user_id = ?
              AND reward_key LIKE 'auto:winner:%'
              AND granted_at >= ?
            """,
            (
                winner_id,
                now - DUEL_REWARD_WINDOW_SECONDS,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

        if int(row[0]) >= DUEL_REWARD_DAILY_LIMIT:
            return "daily_limit"

        cursor = await db.execute(
            """
            SELECT user_id
            FROM activity_participants
            WHERE activity_id = ?
              AND user_id != ?
            LIMIT 1
            """,
            (
                activity_id,
                winner_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

        if row is None:
            return "not_found"

        opponent_id = int(row[0])

        cursor = await db.execute(
            """
            SELECT MAX(p.granted_at)
            FROM activity_payouts AS p
            JOIN activity_participants AS winner
              ON winner.activity_id = p.activity_id
             AND winner.user_id = ?
            JOIN activity_participants AS opponent
              ON opponent.activity_id = p.activity_id
             AND opponent.user_id = ?
            JOIN activities AS a
              ON a.activity_id = p.activity_id
            WHERE a.guild_id = ?
              AND a.type = 'duel'
              AND p.reward_key LIKE 'auto:winner:%'
            """,
            (
                winner_id,
                opponent_id,
                guild_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

        last_pair_reward = (
            int(row[0])
            if row is not None
            and row[0] is not None
            else None
        )

        if (
            last_pair_reward is not None
            and now - last_pair_reward
            < DUEL_PAIR_REWARD_COOLDOWN_SECONDS
        ):
            return "pair_cooldown"

    return "allowed"


async def reward_duel_winner_automatically(
    guild_id: int,
    activity_id: int,
    winner_id: int,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    status = await check_duel_reward_allowed(
        guild_id=guild_id,
        activity_id=activity_id,
        winner_id=winner_id,
    )

    if status != "allowed":
        return [
            ActivityRewardResult(
                status=status,
                user_id=winner_id,
                reward_kind="duel",
                amount=0,
            )
        ]

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
