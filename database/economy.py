import time

import aiosqlite

from database.connection import DB_PATH

async def change_currency(
    guild_id: int,
    user_id: int,
    amount: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                currency
            )
            VALUES (?, ?, MAX(?, 0))

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                currency = MAX(currency + ?, 0)
            """,
            (
                guild_id,
                user_id,
                amount,
                amount
            )
        )

        await db.commit()

async def get_balance(
    guild_id: int,
    user_id: int
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
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
                user_id
            )
        )

        await db.commit()

        cursor = await db.execute(
            """
            SELECT currency
            FROM member_stats
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (
                guild_id,
                user_id
            )
        )

        row = await cursor.fetchone()

    return row[0]

async def change_balance(
    guild_id: int,
    user_id: int,
    amount: int,
    reason: str,
    description: str | None = None,
    actor_id: int | None = None
) -> int | None:
    if amount == 0:
        raise ValueError(
            "Изменение баланса не может быть равно 0"
        )

    if not reason:
        raise ValueError(
            "Для операции должна быть указана причина"
        )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")

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
                user_id
            )
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
                user_id
            )
        )

        row = await cursor.fetchone()

        current_balance = row[0]
        new_balance = current_balance + amount

        if new_balance < 0:
            await db.rollback()
            return None

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
                user_id
            )
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
                reason,
                description,
                actor_id,
                int(time.time())
            )
        )

        await db.commit()

    return new_balance