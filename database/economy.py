import time

from database.connection import get_db


# =========================================================
# BALANCE
# =========================================================

async def get_balance(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Возвращает текущий баланс пользователя.

    Если пользователя ещё нет в member_stats,
    создаёт его с нулевым балансом.
    """

    async with get_db() as db:
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

        cursor = await db.execute(
            """
            SELECT currency
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
        await db.commit()

    if row is None:
        raise RuntimeError(
            "Не удалось получить баланс пользователя"
        )

    return int(row[0])


# =========================================================
# CHANGE BALANCE
# =========================================================

async def change_balance(
    guild_id: int,
    user_id: int,
    amount: int,
    reason: str,
    description: str | None = None,
    actor_id: int | None = None,
) -> int | None:
    """
    Атомарно изменяет баланс пользователя.

    Каждая успешная операция записывается
    в currency_transactions.

    Возвращает:
        int
            новый баланс;

        None
            если операция сделала бы
            баланс отрицательным.
    """

    # =====================================================
    # VALIDATION
    # =====================================================

    if amount == 0:
        raise ValueError(
            "Изменение баланса не может быть равно 0"
        )

    if not reason or not reason.strip():
        raise ValueError(
            "Для операции должна быть указана причина"
        )

    # =====================================================
    # TRANSACTION
    # =====================================================

    async with get_db() as db:
        try:
            # BEGIN IMMEDIATE берёт write-lock заранее.
            #
            # Это важно для экономики:
            # два одновременных списания не должны
            # прочитать один и тот же старый баланс.
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            # =================================================
            # MEMBER
            # =================================================

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

            # =================================================
            # CURRENT BALANCE
            # =================================================

            cursor = await db.execute(
                """
                SELECT currency
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
                    "Не удалось найти пользователя "
                    "после его создания"
                )

            current_balance = int(
                row[0]
            )

            new_balance = (
                current_balance
                + amount
            )

            # =================================================
            # NEGATIVE BALANCE PROTECTION
            # =================================================

            if new_balance < 0:
                await db.rollback()

                return None

            # =================================================
            # UPDATE BALANCE
            # =================================================

            await db.execute(
                """
                UPDATE member_stats
                SET currency = ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    new_balance,
                    guild_id,
                    user_id,
                ),
            )

            # =================================================
            # TRANSACTION HISTORY
            # =================================================

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
                    reason.strip(),
                    description,
                    actor_id,
                    int(time.time()),
                ),
            )

            # =================================================
            # COMMIT
            # =================================================

            await db.commit()

            return new_balance

        except Exception:
            # Если ошибка произошла между изменением
            # баланса и записью transaction history,
            # откатывается ВСЯ операция.
            await db.rollback()

            raise