import time

from dataclasses import dataclass

from config.economy import REASON_EVENT

from database.connection import get_db

from utils.leveling import level_from_xp


REWARD_KINDS = {
    "currency",
    "xp",
    "case",
}


@dataclass(frozen=True)
class ActivityRewardResult:
    status: str

    user_id: int

    reward_kind: str
    amount: int

    new_level: int | None = None
    cases_gained: int = 0


async def grant_activity_reward(
    guild_id: int,
    activity_id: int,
    user_id: int,
    reward_key: str,
    reward_kind: str,
    amount: int,
    actor_id: int | None = None,
) -> ActivityRewardResult:
    if reward_kind not in REWARD_KINDS:
        raise ValueError(
            f"Неизвестный тип награды: "
            f"{reward_kind}"
        )

    if amount <= 0:
        raise ValueError(
            "Размер награды должен быть больше 0"
        )

    reward_key = reward_key.strip()

    if not reward_key:
        raise ValueError(
            "reward_key не может быть пустым"
        )

    now = int(
        time.time()
    )

    new_level = None
    cases_gained = 0

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            # Проверяем активность
            cursor = await db.execute(
                """
                SELECT status
                FROM activities
                WHERE guild_id = ?
                  AND activity_id = ?
                """,
                (
                    guild_id,
                    activity_id,
                ),
            )

            activity_row = (
                await cursor.fetchone()
            )

            await cursor.close()

            if activity_row is None:
                await db.rollback()

                return ActivityRewardResult(
                    status="not_found",
                    user_id=user_id,
                    reward_kind=reward_kind,
                    amount=amount,
                )

            if str(activity_row[0]) != "finished":
                await db.rollback()

                return ActivityRewardResult(
                    status="not_finished",
                    user_id=user_id,
                    reward_kind=reward_kind,
                    amount=amount,
                )

            # Пользователь должен участвовать
            cursor = await db.execute(
                """
                SELECT 1
                FROM activity_participants
                WHERE activity_id = ?
                  AND user_id = ?
                """,
                (
                    activity_id,
                    user_id,
                ),
            )

            participant = (
                await cursor.fetchone()
            )

            await cursor.close()

            if participant is None:
                await db.rollback()

                return ActivityRewardResult(
                    status="not_participant",
                    user_id=user_id,
                    reward_kind=reward_kind,
                    amount=amount,
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

            # Сначала резервируем выплату.
            # Если что-то дальше сломается,
            # вся транзакция откатится.
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO activity_payouts (
                    activity_id,
                    user_id,
                    reward_key,
                    reward_kind,
                    amount,
                    actor_id,
                    granted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    user_id,
                    reward_key,
                    reward_kind,
                    amount,
                    actor_id,
                    now,
                ),
            )

            was_added = (
                cursor.rowcount == 1
            )

            await cursor.close()

            if not was_added:
                await db.rollback()

                return ActivityRewardResult(
                    status="already_granted",
                    user_id=user_id,
                    reward_kind=reward_kind,
                    amount=amount,
                )

            if reward_kind == "currency":
                await db.execute(
                    """
                    UPDATE member_stats
                    SET currency = currency + ?
                    WHERE guild_id = ?
                      AND user_id = ?
                    """,
                    (
                        amount,
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
                        amount,
                        REASON_EVENT,
                        (
                            f"activity:{activity_id}:"
                            f"{reward_key}"
                        ),
                        actor_id,
                        now,
                    ),
                )

            elif reward_kind == "case":
                await db.execute(
                    """
                    UPDATE member_stats
                    SET eden_cases = eden_cases + ?
                    WHERE guild_id = ?
                      AND user_id = ?
                    """,
                    (
                        amount,
                        guild_id,
                        user_id,
                    ),
                )

            elif reward_kind == "xp":
                cursor = await db.execute(
                    """
                    SELECT xp
                    FROM member_stats
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

                if row is None:
                    raise RuntimeError(
                        "Не удалось получить XP"
                    )

                old_xp = int(
                    row[0]
                )

                old_level = level_from_xp(
                    old_xp
                )

                new_xp = (
                    old_xp
                    + amount
                )

                new_level = level_from_xp(
                    new_xp
                )

                cases_gained = max(
                    0,
                    new_level - old_level,
                )

                await db.execute(
                    """
                    UPDATE member_stats
                    SET
                        xp = ?,
                        eden_cases = eden_cases + ?
                    WHERE guild_id = ?
                      AND user_id = ?
                    """,
                    (
                        new_xp,
                        cases_gained,
                        guild_id,
                        user_id,
                    ),
                )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    return ActivityRewardResult(
        status="granted",
        user_id=user_id,
        reward_kind=reward_kind,
        amount=amount,
        new_level=new_level,
        cases_gained=cases_gained,
    )


async def reward_activity_participants(
    guild_id: int,
    activity_id: int,
    reward_kind: str,
    amount: int,
    actor_id: int | None = None,
) -> list[ActivityRewardResult]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT user_id
            FROM activity_participants
            WHERE activity_id = ?
            ORDER BY joined_at ASC
            """,
            (
                activity_id,
            ),
        )

        rows = await cursor.fetchall()
        await cursor.close()

    reward_key = (
        f"participant:{reward_kind}"
    )

    results = []

    for row in rows:
        user_id = int(
            row[0]
        )

        result = await grant_activity_reward(
            guild_id=guild_id,
            activity_id=activity_id,
            user_id=user_id,
            reward_key=reward_key,
            reward_kind=reward_kind,
            amount=amount,
            actor_id=actor_id,
        )

        results.append(
            result
        )

    return results