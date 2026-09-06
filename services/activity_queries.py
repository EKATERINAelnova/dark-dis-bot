from database.connection import get_db

from services.activities import (
    Activity,
    activity_from_row,
)


async def get_active_activities(
    guild_id: int,
    activity_type: str,
    limit: int = 10,
) -> list[Activity]:
    limit = max(
        1,
        min(limit, 25),
    )

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                activity_id,
                guild_id,
                type,
                title,
                description,
                host_id,
                status,
                max_participants,
                starts_at,
                channel_id,
                message_id,
                reward_preset,
                created_at
            FROM activities
            WHERE guild_id = ?
              AND type = ?
              AND status IN ('open', 'running')
            ORDER BY activity_id DESC
            LIMIT ?
            """,
            (
                guild_id,
                activity_type,
                limit,
            ),
        )

        rows = await cursor.fetchall()
        await cursor.close()

    return [
        activity_from_row(row)
        for row in rows
    ]
