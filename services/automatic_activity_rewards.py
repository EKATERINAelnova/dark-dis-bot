import time

from config.economy import (
    DUEL_MIN_DURATION_SECONDS,
    DUEL_PAIR_REWARD_COOLDOWN_SECONDS,
    DUEL_REWARD_DAILY_LIMIT,
    DUEL_REWARD_WINDOW_SECONDS,
    DUEL_WIN_REWARD,
    EVENT_REWARD_PRESETS,
)
from database.connection import get_db
from services.achievements import (
    check_activity_participant_achievements,
)
from services.activities import Activity
from services.activity_rewards import (
    ActivityRewardResult,
    grant_activity_reward,
    reward_activity_participants,
)
from services.reward_decisions import (
    get_reward_decision,
    save_reward_decision,
)


DUEL_REWARD_POLICY = "duel:auto"


def get_event_rewards(
    reward_preset: str | None,
) -> dict[str, int]:
    """
    Преобразует ключ пресета EVENT в набор наград.
    """

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


async def reward_event_automatically(
    activity: Activity,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    results = []

    try:
        rewards = get_event_rewards(
            activity.reward_preset
        )

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

    finally:
        try:
            await check_activity_participant_achievements(
                guild_id=activity.guild_id,
                activity_id=activity.activity_id,
            )
        except Exception as error:
            print(
                f"[EVENT ACHIEVEMENTS] {error}"
            )


async def check_duel_reward_allowed(
    guild_id: int,
    activity_id: int,
    winner_id: int,
) -> str:
    saved_status = await get_reward_decision(
        activity_id=activity_id,
        user_id=winner_id,
        policy_key=DUEL_REWARD_POLICY,
    )

    if saved_status is not None:
        return saved_status

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                a.starts_at,
                r.confirmed_at
            FROM activities AS a
            JOIN activity_results AS r
              ON r.activity_id = a.activity_id
            WHERE a.guild_id = ?
              AND a.activity_id = ?
              AND a.type = 'duel'
              AND r.status = 'confirmed'
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

        reference_time = (
            int(row[1])
            if row[1] is not None
            else int(time.time())
        )

        if (
            starts_at is None
            or reference_time - starts_at
            < DUEL_MIN_DURATION_SECONDS
        ):
            return await save_reward_decision(
                activity_id=activity_id,
                user_id=winner_id,
                policy_key=DUEL_REWARD_POLICY,
                status="too_short",
            )

        cursor = await db.execute(
            """
            SELECT COUNT(DISTINCT p.activity_id)
            FROM activity_payouts AS p
            JOIN activities AS a
              ON a.activity_id = p.activity_id
            WHERE a.guild_id = ?
              AND a.type = 'duel'
              AND p.user_id = ?
              AND p.activity_id != ?
              AND p.reward_key LIKE 'auto:winner:%'
              AND p.granted_at >= ?
              AND p.granted_at <= ?
            """,
            (
                guild_id,
                winner_id,
                activity_id,
                reference_time - DUEL_REWARD_WINDOW_SECONDS,
                reference_time,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

        if int(row[0] or 0) >= DUEL_REWARD_DAILY_LIMIT:
            return await save_reward_decision(
                activity_id=activity_id,
                user_id=winner_id,
                policy_key=DUEL_REWARD_POLICY,
                status="daily_limit",
            )

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
              AND p.activity_id != ?
              AND p.reward_key LIKE 'auto:winner:%'
              AND p.granted_at <= ?
            """,
            (
                winner_id,
                opponent_id,
                guild_id,
                activity_id,
                reference_time,
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
            and reference_time - last_pair_reward
            < DUEL_PAIR_REWARD_COOLDOWN_SECONDS
        ):
            return await save_reward_decision(
                activity_id=activity_id,
                user_id=winner_id,
                policy_key=DUEL_REWARD_POLICY,
                status="pair_cooldown",
            )

    return await save_reward_decision(
        activity_id=activity_id,
        user_id=winner_id,
        policy_key=DUEL_REWARD_POLICY,
        status="allowed",
    )


async def reward_duel_winner_automatically(
    guild_id: int,
    activity_id: int,
    winner_id: int,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    try:
        await check_activity_participant_achievements(
            guild_id=guild_id,
            activity_id=activity_id,
        )
    except Exception as error:
        print(
            f"[DUEL ACHIEVEMENTS] {error}"
        )

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
