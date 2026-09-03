import time

from dataclasses import dataclass

from database.connection import get_db

from services.activities import (
    Activity,
    get_activity,
)


@dataclass(frozen=True)
class DuelCreateResult:
    status: str
    activity: Activity | None = None


async def create_duel(
    guild_id: int,
    challenger_id: int,
    opponent_id: int,
    title: str,
) -> DuelCreateResult:
    if challenger_id == opponent_id:
        return DuelCreateResult(
            status="same_user"
        )

    title = title.strip()

    if not title:
        title = "DUEL"

    title = title[:100]

    now = int(
        time.time()
    )

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            # У вызывающего уже есть дуэль
            cursor = await db.execute(
                """
                SELECT a.activity_id
                FROM activities AS a
                JOIN activity_participants AS p
                  ON p.activity_id = a.activity_id
                WHERE a.guild_id = ?
                  AND a.type = 'duel'
                  AND a.status IN (
                      'open',
                      'running'
                  )
                  AND p.user_id = ?
                LIMIT 1
                """,
                (
                    guild_id,
                    challenger_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is not None:
                await db.rollback()

                return DuelCreateResult(
                    status="challenger_busy"
                )

            # У соперника уже есть дуэль
            cursor = await db.execute(
                """
                SELECT a.activity_id
                FROM activities AS a
                JOIN activity_participants AS p
                  ON p.activity_id = a.activity_id
                WHERE a.guild_id = ?
                  AND a.type = 'duel'
                  AND a.status IN (
                      'open',
                      'running'
                  )
                  AND p.user_id = ?
                LIMIT 1
                """,
                (
                    guild_id,
                    opponent_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is not None:
                await db.rollback()

                return DuelCreateResult(
                    status="opponent_busy"
                )

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
                    "duel",
                    title,
                    "",
                    challenger_id,
                    "open",
                    2,
                    None,
                    now,
                ),
            )

            activity_id = (
                cursor.lastrowid
            )

            await cursor.close()

            if activity_id is None:
                raise RuntimeError(
                    "Не удалось создать DUEL"
                )

            await db.executemany(
                """
                INSERT INTO activity_participants (
                    activity_id,
                    user_id,
                    role,
                    joined_at
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        activity_id,
                        challenger_id,
                        "challenger",
                        now,
                    ),
                    (
                        activity_id,
                        opponent_id,
                        "opponent",
                        now,
                    ),
                ],
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    activity = await get_activity(
        guild_id=guild_id,
        activity_id=activity_id,
    )

    if activity is None:
        raise RuntimeError(
            "Созданный DUEL не найден"
        )

    return DuelCreateResult(
        status="created",
        activity=activity,
    )


async def get_duel_players(
    activity_id: int,
) -> tuple[int, int] | None:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                user_id,
                role
            FROM activity_participants
            WHERE activity_id = ?
              AND role IN (
                  'challenger',
                  'opponent'
              )
            """,
            (
                activity_id,
            ),
        )

        rows = await cursor.fetchall()
        await cursor.close()

    challenger_id = None
    opponent_id = None

    for row in rows:
        user_id = int(
            row[0]
        )

        role = str(
            row[1]
        )

        if role == "challenger":
            challenger_id = user_id

        elif role == "opponent":
            opponent_id = user_id

    if (
        challenger_id is None
        or opponent_id is None
    ):
        return None

    return (
        challenger_id,
        opponent_id,
    )