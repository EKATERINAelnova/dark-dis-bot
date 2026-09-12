import time

from database.connection import get_db


async def get_reward_decision(
    activity_id: int,
    user_id: int,
    policy_key: str,
) -> str | None:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT status
            FROM activity_reward_decisions
            WHERE activity_id = ?
              AND user_id = ?
              AND policy_key = ?
            """,
            (
                activity_id,
                user_id,
                policy_key,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return None

    return str(row[0])


async def save_reward_decision(
    activity_id: int,
    user_id: int,
    policy_key: str,
    status: str,
) -> str:
    """
    Фиксирует первое решение reward-policy.

    Повторные вызовы всегда возвращают первоначальный результат,
    поэтому retry не может обойти cooldown или суточный лимит.
    """

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            await db.execute(
                """
                INSERT OR IGNORE INTO activity_reward_decisions (
                    activity_id,
                    user_id,
                    policy_key,
                    status,
                    decided_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    user_id,
                    policy_key,
                    status,
                    int(time.time()),
                ),
            )

            cursor = await db.execute(
                """
                SELECT status
                FROM activity_reward_decisions
                WHERE activity_id = ?
                  AND user_id = ?
                  AND policy_key = ?
                """,
                (
                    activity_id,
                    user_id,
                    policy_key,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                raise RuntimeError(
                    "Не удалось сохранить решение по награде"
                )

            await db.commit()
            return str(row[0])

        except Exception:
            await db.rollback()
            raise
