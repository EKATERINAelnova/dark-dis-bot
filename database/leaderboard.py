from typing import Literal

from database.connection import get_db
from database.models import MemberStats


# =========================================================
# TYPES
# =========================================================

LeaderboardCategory = Literal[
    "xp",
    "messages",
    "voice",
    "currency",
]


# =========================================================
# SORTING
# =========================================================

ORDER_BY = {
    "xp": """
        xp DESC,
        messages DESC,
        voice_seconds DESC,
        user_id ASC
    """,

    "messages": """
        messages DESC,
        xp DESC,
        user_id ASC
    """,

    "voice": """
        voice_seconds DESC,
        xp DESC,
        user_id ASC
    """,

    "currency": """
        currency DESC,
        xp DESC,
        user_id ASC
    """,
}


# =========================================================
# VALIDATION
# =========================================================

def validate_category(
    category: LeaderboardCategory,
) -> None:
    """
    Проверяет существование категории рейтинга.
    """

    if category not in ORDER_BY:
        raise ValueError(
            f"Неизвестная категория рейтинга: "
            f"{category}"
        )


# =========================================================
# LEADERBOARD
# =========================================================

async def get_leaderboard(
    guild_id: int,
    category: LeaderboardCategory = "xp",
    limit: int = 10,
) -> list[MemberStats]:
    """
    Возвращает участников,
    отсортированных по выбранной категории.
    """

    validate_category(
        category
    )

    if limit <= 0:
        return []

    # Защита от случайного запроса
    # огромного количества строк.
    limit = min(
        limit,
        100,
    )

    order_by = ORDER_BY[
        category
    ]

    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT
                guild_id,
                user_id,
                messages,
                voice_seconds,
                xp,
                currency,
                eden_cases
            FROM member_stats
            WHERE guild_id = ?
            ORDER BY {order_by}
            LIMIT ?
            """,
            (
                guild_id,
                limit,
            ),
        )

        rows = await cursor.fetchall()

        await cursor.close()

    return [
        MemberStats(
            guild_id=int(row[0]),
            user_id=int(row[1]),
            messages=int(row[2]),
            voice_seconds=int(row[3]),
            xp=int(row[4]),
            currency=int(row[5]),
            eden_cases=int(row[6]),
        )
        for row in rows
    ]


# =========================================================
# RANK
# =========================================================

async def get_leaderboard_rank(
    guild_id: int,
    user_id: int,
    category: LeaderboardCategory = "xp",
) -> int:
    """
    Возвращает точное место пользователя
    в выбранной категории.

    Используется та же сортировка,
    что и в get_leaderboard().
    """

    validate_category(
        category
    )

    order_by = ORDER_BY[
        category
    ]

    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT ranking_position
            FROM (
                SELECT
                    user_id,

                    ROW_NUMBER() OVER (
                        ORDER BY {order_by}
                    ) AS ranking_position

                FROM member_stats
                WHERE guild_id = ?
            )
            WHERE user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()

        await cursor.close()

    # Пользователь ещё отсутствует
    # в member_stats.
    if row is None:
        return 0

    return int(
        row[0]
    )