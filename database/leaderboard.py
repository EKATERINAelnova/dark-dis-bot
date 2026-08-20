from typing import Literal

import aiosqlite

from database.connection import DB_PATH
from database.models import MemberStats


LeaderboardCategory = Literal[
    "xp",
    "messages",
    "voice",
    "currency",
]


ORDER_BY = {
    "xp": """
        xp DESC,
        messages DESC,
        voice_seconds DESC
    """,

    "messages": """
        messages DESC,
        xp DESC
    """,

    "voice": """
        voice_seconds DESC,
        xp DESC
    """,

    "currency": """
        currency DESC,
        xp DESC
    """,
}


RANK_COLUMN = {
    "xp": "xp",
    "messages": "messages",
    "voice": "voice_seconds",
    "currency": "currency",
}


async def get_leaderboard(
    guild_id: int,
    category: LeaderboardCategory = "xp",
    limit: int = 10,
) -> list[MemberStats]:
    if category not in ORDER_BY:
        raise ValueError(
            f"Unknown leaderboard category: {category}"
        )

    order_by = ORDER_BY[category]

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"""
            SELECT
                guild_id,
                user_id,
                messages,
                voice_seconds,
                xp,
                currency
            FROM member_stats
            WHERE guild_id = ?
            ORDER BY {order_by}
            LIMIT ?
            """,
            (
                guild_id,
                limit,
            )
        )

        rows = await cursor.fetchall()

    return [
        MemberStats(
            guild_id=row[0],
            user_id=row[1],
            messages=row[2],
            voice_seconds=row[3],
            xp=row[4],
            currency=row[5],
        )
        for row in rows
    ]


async def get_leaderboard_rank(
    guild_id: int,
    user_id: int,
    category: LeaderboardCategory = "xp",
) -> int:
    if category not in RANK_COLUMN:
        raise ValueError(
            f"Unknown leaderboard category: {category}"
        )

    column = RANK_COLUMN[category]

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"""
            SELECT {column}
            FROM member_stats
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (
                guild_id,
                user_id,
            )
        )

        row = await cursor.fetchone()

        if row is None:
            return 0

        value = row[0]

        cursor = await db.execute(
            f"""
            SELECT COUNT(*)
            FROM member_stats
            WHERE guild_id = ?
              AND {column} > ?
            """,
            (
                guild_id,
                value,
            )
        )

        row = await cursor.fetchone()

    return row[0] + 1