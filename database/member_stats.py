import aiosqlite

from database.connection import DB_PATH
from database.models import MemberStats


async def get_or_create_member(
    guild_id: int,
    user_id: int
) -> MemberStats:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO member_stats (
                guild_id,
                user_id
            )
            VALUES (?, ?)
            """,
            (guild_id, user_id)
        )

        await db.commit()

        cursor = await db.execute(
            """
            SELECT
                guild_id,
                user_id,
                messages,
                voice_seconds,
                xp,
                currency
            FROM member_stats
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (guild_id, user_id)
        )

        row = await cursor.fetchone()

    return MemberStats(
        guild_id=row[0],
        user_id=row[1],
        messages=row[2],
        voice_seconds=row[3],
        xp=row[4],
        currency=row[5]
    )


async def get_member_stats(
    guild_id: int,
    user_id: int
) -> MemberStats:
    return await get_or_create_member(
        guild_id,
        user_id
    )


async def increment_messages(
    guild_id: int,
    user_id: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                messages
            )
            VALUES (?, ?, 1)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                messages = messages + 1
            """,
            (guild_id, user_id)
        )

        await db.commit()


async def add_voice_seconds(
    guild_id: int,
    user_id: int,
    seconds: int
) -> None:
    if seconds <= 0:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                voice_seconds
            )
            VALUES (?, ?, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                voice_seconds = voice_seconds + excluded.voice_seconds
            """,
            (guild_id, user_id, seconds)
        )

        await db.commit()


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