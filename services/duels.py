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


@dataclass(frozen=True)
class DuelResult:
    guild_id: int
    activity_id: int

    winner_id: int
    submitted_by: int
    confirmed_by: int | None

    status: str

    created_at: int
    confirmed_at: int | None


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

    title = title.strip() or "DUEL"
    title = title[:100]

    now = int(time.time())

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            for user_id, busy_status in (
                (
                    challenger_id,
                    "challenger_busy",
                ),
                (
                    opponent_id,
                    "opponent_busy",
                ),
            ):
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
                        user_id,
                    ),
                )

                row = await cursor.fetchone()
                await cursor.close()

                if row is not None:
                    await db.rollback()

                    return DuelCreateResult(
                        status=busy_status
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

            activity_id = cursor.lastrowid
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
        user_id = int(row[0])
        role = str(row[1])

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


def duel_result_from_row(
    row,
) -> DuelResult:
    return DuelResult(
        guild_id=int(row[0]),
        activity_id=int(row[1]),
        winner_id=int(row[2]),
        submitted_by=int(row[3]),
        confirmed_by=(
            int(row[4])
            if row[4] is not None
            else None
        ),
        status=str(row[5]),
        created_at=int(row[6]),
        confirmed_at=(
            int(row[7])
            if row[7] is not None
            else None
        ),
    )


async def get_duel_result(
    activity_id: int,
) -> DuelResult | None:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                a.guild_id,
                r.activity_id,
                r.winner_user_id,
                r.submitted_by,
                r.confirmed_by,
                r.status,
                r.created_at,
                r.confirmed_at
            FROM activity_results AS r
            JOIN activities AS a
              ON a.activity_id = r.activity_id
            WHERE r.activity_id = ?
              AND a.type = 'duel'
            """,
            (
                activity_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return None

    return duel_result_from_row(
        row
    )


async def get_pending_duel_results(
    guild_id: int | None = None,
) -> list[DuelResult]:
    query = """
        SELECT
            a.guild_id,
            r.activity_id,
            r.winner_user_id,
            r.submitted_by,
            r.confirmed_by,
            r.status,
            r.created_at,
            r.confirmed_at
        FROM activity_results AS r
        JOIN activities AS a
          ON a.activity_id = r.activity_id
        WHERE a.type = 'duel'
          AND a.status = 'running'
          AND r.status = 'pending'
          AND a.message_id IS NOT NULL
    """

    params = []

    if guild_id is not None:
        query += (
            " AND a.guild_id = ?"
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
        duel_result_from_row(row)
        for row in rows
    ]


async def propose_duel_result(
    guild_id: int,
    activity_id: int,
    winner_id: int,
    submitted_by: int,
) -> tuple[str, DuelResult | None]:
    now = int(time.time())

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
                  AND type = 'duel'
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

            if str(row[0]) != "running":
                await db.rollback()

                return (
                    "not_running",
                    None,
                )

            cursor = await db.execute(
                """
                SELECT user_id
                FROM activity_participants
                WHERE activity_id = ?
                """,
                (
                    activity_id,
                ),
            )

            rows = await cursor.fetchall()
            await cursor.close()

            participants = {
                int(row[0])
                for row in rows
            }

            if submitted_by not in participants:
                await db.rollback()

                return (
                    "not_participant",
                    None,
                )

            if winner_id not in participants:
                await db.rollback()

                return (
                    "invalid_winner",
                    None,
                )

            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO activity_results (
                    activity_id,
                    winner_user_id,
                    submitted_by,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    winner_id,
                    submitted_by,
                    "pending",
                    now,
                ),
            )

            added = (
                cursor.rowcount == 1
            )

            await cursor.close()

            if not added:
                await db.rollback()

                existing = await get_duel_result(
                    activity_id
                )

                return (
                    "already_pending",
                    existing,
                )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    result = await get_duel_result(
        activity_id
    )

    return (
        "created",
        result,
    )


async def confirm_duel_result(
    guild_id: int,
    activity_id: int,
    confirmed_by: int,
) -> tuple[str, Activity | None]:
    now = int(time.time())

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    a.status,
                    r.status
                FROM activity_results AS r
                JOIN activities AS a
                  ON a.activity_id = r.activity_id
                WHERE a.guild_id = ?
                  AND a.activity_id = ?
                  AND a.type = 'duel'
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

            activity_status = str(
                row[0]
            )

            result_status = str(
                row[1]
            )

            if activity_status != "running":
                await db.rollback()

                return (
                    "not_running",
                    None,
                )

            if result_status != "pending":
                await db.rollback()

                return (
                    "not_pending",
                    None,
                )

            await db.execute(
                """
                UPDATE activity_results
                SET
                    status = 'confirmed',
                    confirmed_by = ?,
                    confirmed_at = ?
                WHERE activity_id = ?
                """,
                (
                    confirmed_by,
                    now,
                    activity_id,
                ),
            )

            await db.execute(
                """
                UPDATE activities
                SET status = 'finished'
                WHERE guild_id = ?
                  AND activity_id = ?
                  AND status = 'running'
                """,
                (
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
        "confirmed",
        activity,
    )


async def discard_duel_result(
    guild_id: int,
    activity_id: int,
) -> str:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                DELETE FROM activity_results
                WHERE activity_id = ?
                  AND status = 'pending'
                  AND EXISTS (
                      SELECT 1
                      FROM activities
                      WHERE activity_id = ?
                        AND guild_id = ?
                        AND type = 'duel'
                  )
                """,
                (
                    activity_id,
                    activity_id,
                    guild_id,
                ),
            )

            removed = (
                cursor.rowcount == 1
            )

            await cursor.close()

            if not removed:
                await db.rollback()
                return "not_found"

            await db.commit()

            return "discarded"

        except Exception:
            await db.rollback()
            raise