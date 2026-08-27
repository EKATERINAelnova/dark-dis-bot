import time

from dataclasses import dataclass

from database.connection import get_db


ACTIVITY_TYPES = {
    "event",
    "duel",
    "close",
    "tribune",
}


ACTIVITY_TRANSITIONS = {
    "open": {
        "running",
        "cancelled",
    },
    "running": {
        "finished",
        "cancelled",
    },
}


@dataclass(frozen=True)
class Activity:
    activity_id: int

    guild_id: int
    type: str

    title: str
    description: str

    host_id: int
    status: str

    max_participants: int | None
    starts_at: int | None

    channel_id: int | None
    message_id: int | None

    created_at: int


@dataclass(frozen=True)
class ActivityParticipant:
    user_id: int
    role: str
    joined_at: int


def activity_from_row(
    row,
) -> Activity:
    return Activity(
        activity_id=int(row[0]),
        guild_id=int(row[1]),
        type=str(row[2]),
        title=str(row[3]),
        description=str(row[4]),
        host_id=int(row[5]),
        status=str(row[6]),
        max_participants=(
            int(row[7])
            if row[7] is not None
            else None
        ),
        starts_at=(
            int(row[8])
            if row[8] is not None
            else None
        ),
        channel_id=(
            int(row[9])
            if row[9] is not None
            else None
        ),
        message_id=(
            int(row[10])
            if row[10] is not None
            else None
        ),
        created_at=int(row[11]),
    )


async def create_activity(
    guild_id: int,
    activity_type: str,
    title: str,
    description: str,
    host_id: int,
    max_participants: int | None = None,
    starts_at: int | None = None,
) -> Activity:
    if activity_type not in ACTIVITY_TYPES:
        raise ValueError(
            f"Неизвестный тип активности: "
            f"{activity_type}"
        )

    if (
        max_participants is not None
        and max_participants < 1
    ):
        raise ValueError(
            "Лимит участников должен быть больше 0"
        )

    now = int(
        time.time()
    )

    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO activities (
                guild_id,
                type,
                title,
                description,
                host_id,
                status,
                max_participants,
                starts_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                activity_type,
                title,
                description,
                host_id,
                "open",
                max_participants,
                starts_at,
                now,
            ),
        )

        activity_id = cursor.lastrowid

        await cursor.close()
        await db.commit()

    if activity_id is None:
        raise RuntimeError(
            "Не удалось создать активность"
        )

    activity = await get_activity(
        guild_id=guild_id,
        activity_id=activity_id,
    )

    if activity is None:
        raise RuntimeError(
            "Созданная активность не найдена"
        )

    return activity


async def get_activity(
    guild_id: int,
    activity_id: int,
) -> Activity | None:
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
                created_at
            FROM activities
            WHERE guild_id = ?
              AND activity_id = ?
            """,
            (
                guild_id,
                activity_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return None

    return activity_from_row(
        row
    )


async def get_activity_participants(
    activity_id: int,
) -> list[ActivityParticipant]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                user_id,
                role,
                joined_at
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

    return [
        ActivityParticipant(
            user_id=int(row[0]),
            role=str(row[1]),
            joined_at=int(row[2]),
        )
        for row in rows
    ]


async def join_activity(
    guild_id: int,
    activity_id: int,
    user_id: int,
    role: str = "participant",
) -> str:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    status,
                    max_participants
                FROM activities
                WHERE guild_id = ?
                  AND activity_id = ?
                """,
                (
                    guild_id,
                    activity_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                await db.rollback()
                return "not_found"

            status = str(
                row[0]
            )

            max_participants = (
                int(row[1])
                if row[1] is not None
                else None
            )

            if status != "open":
                await db.rollback()
                return "closed"

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

            exists = await cursor.fetchone()
            await cursor.close()

            if exists is not None:
                await db.rollback()
                return "already_joined"

            if max_participants is not None:
                cursor = await db.execute(
                    """
                    SELECT COUNT(*)
                    FROM activity_participants
                    WHERE activity_id = ?
                    """,
                    (
                        activity_id,
                    ),
                )

                count_row = await cursor.fetchone()
                await cursor.close()

                count = int(
                    count_row[0]
                )

                if count >= max_participants:
                    await db.rollback()
                    return "full"

            await db.execute(
                """
                INSERT INTO activity_participants (
                    activity_id,
                    user_id,
                    role,
                    joined_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    activity_id,
                    user_id,
                    role,
                    int(time.time()),
                ),
            )

            await db.commit()

            return "joined"

        except Exception:
            await db.rollback()
            raise


async def leave_activity(
    guild_id: int,
    activity_id: int,
    user_id: int,
) -> str:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

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

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                await db.rollback()
                return "not_found"

            if str(row[0]) != "open":
                await db.rollback()
                return "closed"

            cursor = await db.execute(
                """
                DELETE FROM activity_participants
                WHERE activity_id = ?
                  AND user_id = ?
                """,
                (
                    activity_id,
                    user_id,
                ),
            )

            removed = (
                cursor.rowcount > 0
            )

            await cursor.close()
            await db.commit()

            if removed:
                return "left"

            return "not_joined"

        except Exception:
            await db.rollback()
            raise


async def change_activity_status(
    guild_id: int,
    activity_id: int,
    new_status: str,
) -> tuple[str, Activity | None]:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

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

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                await db.rollback()

                return (
                    "not_found",
                    None,
                )

            current_status = str(
                row[0]
            )

            allowed = ACTIVITY_TRANSITIONS.get(
                current_status,
                set(),
            )

            if new_status not in allowed:
                await db.rollback()

                return (
                    "invalid_transition",
                    None,
                )

            await db.execute(
                """
                UPDATE activities
                SET status = ?
                WHERE guild_id = ?
                  AND activity_id = ?
                """,
                (
                    new_status,
                    guild_id,
                    activity_id,
                ),
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    activity = await get_activity(
        guild_id=guild_id,
        activity_id=activity_id,
    )

    return (
        "changed",
        activity,
    )


async def set_activity_message(
    guild_id: int,
    activity_id: int,
    channel_id: int,
    message_id: int,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE activities
            SET
                channel_id = ?,
                message_id = ?
            WHERE guild_id = ?
              AND activity_id = ?
            """,
            (
                channel_id,
                message_id,
                guild_id,
                activity_id,
            ),
        )

        await db.commit()


async def get_open_activities(
    guild_id: int | None = None,
) -> list[Activity]:
    query = """
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
            created_at
        FROM activities
        WHERE status = 'open'
          AND message_id IS NOT NULL
    """

    params = []

    if guild_id is not None:
        query += (
            " AND guild_id = ?"
        )

        params.append(
            guild_id
        )

    async with get_db() as db:
        cursor = await db.execute(
            query,
            params,
        )

        rows = await cursor.fetchall()
        await cursor.close()

    return [
        activity_from_row(
            row
        )
        for row in rows
    ]