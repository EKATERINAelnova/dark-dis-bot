import secrets
import time

from dataclasses import dataclass

from config.economy import REASON_RITUAL
from database.connection import get_db


RITUAL_COOLDOWN = 24 * 60 * 60


@dataclass(frozen=True)
class RitualReward:
    kind: str
    amount: int
    weight: int


RITUAL_REWARDS = [
    RitualReward(
        kind="currency",
        amount=10,
        weight=40,
    ),
    RitualReward(
        kind="currency",
        amount=20,
        weight=30,
    ),
    RitualReward(
        kind="currency",
        amount=35,
        weight=20,
    ),
    RitualReward(
        kind="case",
        amount=1,
        weight=10,
    ),
]


@dataclass
class RitualResult:
    reward: RitualReward | None
    remaining_seconds: int = 0


randomizer = secrets.SystemRandom()


def roll_ritual_reward() -> RitualReward:
    return randomizer.choices(
        RITUAL_REWARDS,
        weights=[
            reward.weight
            for reward in RITUAL_REWARDS
        ],
        k=1,
    )[0]


async def perform_daily_ritual(
    guild_id: int,
    user_id: int,
) -> RitualResult:
    now = int(time.time())

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            await db.execute(
                """
                INSERT OR IGNORE INTO member_stats (
                    guild_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            await db.execute(
                """
                INSERT OR IGNORE INTO daily_rituals (
                    guild_id,
                    user_id,
                    last_ritual_at
                )
                VALUES (?, ?, 0)
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            cursor = await db.execute(
                """
                SELECT last_ritual_at
                FROM daily_rituals
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            last_ritual_at = int(
                row[0]
            )

            passed = (
                now - last_ritual_at
            )

            if passed < RITUAL_COOLDOWN:
                await db.rollback()

                return RitualResult(
                    reward=None,
                    remaining_seconds=(
                        RITUAL_COOLDOWN
                        - passed
                    ),
                )

            reward = roll_ritual_reward()

            if reward.kind == "currency":
                await db.execute(
                    """
                    UPDATE member_stats
                    SET currency = currency + ?
                    WHERE guild_id = ?
                      AND user_id = ?
                    """,
                    (
                        reward.amount,
                        guild_id,
                        user_id,
                    ),
                )

                await db.execute(
                    """
                    INSERT INTO currency_transactions (
                        guild_id,
                        user_id,
                        amount,
                        reason,
                        description,
                        actor_id,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        user_id,
                        reward.amount,
                        REASON_RITUAL,
                        "daily_ritual",
                        None,
                        now,
                    ),
                )

            elif reward.kind == "case":
                await db.execute(
                    """
                    UPDATE member_stats
                    SET eden_cases = eden_cases + ?
                    WHERE guild_id = ?
                      AND user_id = ?
                    """,
                    (
                        reward.amount,
                        guild_id,
                        user_id,
                    ),
                )

            else:
                raise RuntimeError(
                    f"Неизвестная награда: "
                    f"{reward.kind}"
                )

            await db.execute(
                """
                UPDATE daily_rituals
                SET last_ritual_at = ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    now,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return RitualResult(
                reward=reward
            )

        except Exception:
            await db.rollback()
            raise