import aiosqlite

from database.connection import DB_PATH
from database.models import MemberStats
from config.leveling import VOICE_XP_PER_MINUTE


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

async def record_message(
    guild_id: int,
    user_id: int,
    xp_gain: int = 0
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                messages,
                xp
            )
            VALUES (?, ?, 1, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                messages = messages + 1,
                xp = xp + excluded.xp
            """,
            (
                guild_id,
                user_id,
                xp_gain
            )
        )

        await db.commit()

async def add_voice_seconds(
    guild_id: int,
    user_id: int,
    seconds: int
) -> int:
    if seconds <= 0:
        return 0

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

        cursor = await db.execute(
            """
            SELECT voice_seconds
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

        old_seconds = row[0]
        new_seconds = old_seconds + seconds

        old_minutes = old_seconds // 60
        new_minutes = new_seconds // 60

        earned_minutes = (
            new_minutes - old_minutes
        )

        xp_gain = (
            earned_minutes
            * VOICE_XP_PER_MINUTE
        )

        await db.execute(
            """
            UPDATE member_stats
            SET
                voice_seconds = ?,
                xp = xp + ?
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (
                new_seconds,
                xp_gain,
                guild_id,
                user_id
            )
        )

        await db.commit()

    return xp_gain

async def get_member_rank(
    guild_id: int,
    user_id: int
) -> int:
    stats = await get_or_create_member(
        guild_id,
        user_id
    )

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM member_stats
            WHERE guild_id = ?
              AND xp > ?
            """,
            (
                guild_id,
                stats.xp
            )
        )

        row = await cursor.fetchone()

    return row[0] + 1
