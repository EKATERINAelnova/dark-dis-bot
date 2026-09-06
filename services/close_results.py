import time

from dataclasses import dataclass

from database.connection import get_db

from services.activities import (
    Activity,
    get_activity,
)

from services.close_teams import (
    TEAM_MODE_CAPTAINS,
    get_close_settings,
)


@dataclass(frozen=True)
class CloseResult:
    activity_id: int
    winner_team: str
    submitted_by: int
    confirmed_by: int | None
    status: str
    created_at: int
    confirmed_at: int | None


async def init_close_results() -> None:
    async with get_db() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS close_results (
                activity_id INTEGER PRIMARY KEY,
                winner_team TEXT NOT NULL,
                submitted_by INTEGER NOT NULL,
                confirmed_by INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                confirmed_at INTEGER,

                FOREIGN KEY (activity_id)
                    REFERENCES activities(activity_id)
                    ON DELETE CASCADE
            )
            """
        )

        await db.commit()


async def get_close_result(
    activity_id: int,
) -> CloseResult | None:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                activity_id,
                winner_team,
                submitted_by,
                confirmed_by,
                status,
                created_at,
                confirmed_at
            FROM close_results
            WHERE activity_id = ?
            """,
            (
                activity_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return None

    return CloseResult(
        activity_id=int(row[0]),
        winner_team=str(row[1]),
        submitted_by=int(row[2]),
        confirmed_by=(
            int(row[3])
            if row[3] is not None
            else None
        ),
        status=str(row[4]),
        created_at=int(row[5]),
        confirmed_at=(
            int(row[6])
            if row[6] is not None
            else None
        ),
    )


async def propose_close_result(
    guild_id: int,
    activity_id: int,
    winner_team: str,
    submitted_by: int,
) -> str:
    winner_team = winner_team.lower()

    if winner_team not in {
        "a",
        "b",
    }:
        return "invalid_team"

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
                  AND type = 'close'
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

            if str(row[0]) != "running":
                await db.rollback()
                return "not_running"

            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM activity_participants
                WHERE activity_id = ?
                  AND role = 'participant'
                """,
                (
                    activity_id,
                ),
            )

            waiting_row = await cursor.fetchone()
            await cursor.close()

            if int(waiting_row[0]) > 0:
                await db.rollback()
                return "teams_incomplete"

            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO close_results (
                    activity_id,
                    winner_team,
                    submitted_by,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (
                    activity_id,
                    winner_team,
                    submitted_by,
                    now,
                ),
            )

            created = (
                cursor.rowcount == 1
            )

            await cursor.close()

            if not created:
                await db.rollback()
                return "already_pending"

            await db.commit()
            return "created"

        except Exception:
            await db.rollback()
            raise


async def _get_confirming_team_member(
    activity_id: int,
    winner_team: str,
    user_id: int,
) -> bool:
    loser_roles = (
        ("captain_b", "team_b")
        if winner_team == "a"
        else ("captain_a", "team_a")
    )

    settings = await get_close_settings(
        activity_id
    )

    if settings is None:
        return False

    if settings.team_mode == TEAM_MODE_CAPTAINS:
        expected = (
            settings.captain_b_id
            if winner_team == "a"
            else settings.captain_a_id
        )

        return (
            expected is not None
            and user_id == expected
        )

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM activity_participants
            WHERE activity_id = ?
              AND user_id = ?
              AND role IN (?, ?)
            """,
            (
                activity_id,
                user_id,
                loser_roles[0],
                loser_roles[1],
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    return row is not None


async def confirm_close_result(
    guild_id: int,
    activity_id: int,
    confirmed_by: int,
) -> tuple[str, Activity | None]:
    result = await get_close_result(
        activity_id
    )

    if result is None:
        return (
            "not_found",
            None,
        )

    if result.status != "pending":
        return (
            "not_pending",
            None,
        )

    allowed = await _get_confirming_team_member(
        activity_id=activity_id,
        winner_team=result.winner_team,
        user_id=confirmed_by,
    )

    if not allowed:
        return (
            "not_allowed",
            None,
        )

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
                FROM activities AS a
                JOIN close_results AS r
                  ON r.activity_id = a.activity_id
                WHERE a.guild_id = ?
                  AND a.activity_id = ?
                  AND a.type = 'close'
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

            if str(row[1]) != "pending":
                await db.rollback()
                return (
                    "not_pending",
                    None,
                )

            await db.execute(
                """
                UPDATE close_results
                SET
                    status = 'confirmed',
                    confirmed_by = ?,
                    confirmed_at = ?
                WHERE activity_id = ?
                  AND status = 'pending'
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


async def dispute_close_result(
    guild_id: int,
    activity_id: int,
    disputed_by: int,
) -> str:
    result = await get_close_result(
        activity_id
    )

    if result is None:
        return "not_found"

    if result.status != "pending":
        return "not_pending"

    allowed = await _get_confirming_team_member(
        activity_id=activity_id,
        winner_team=result.winner_team,
        user_id=disputed_by,
    )

    if not allowed:
        return "not_allowed"

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                DELETE FROM close_results
                WHERE activity_id = ?
                  AND status = 'pending'
                  AND EXISTS (
                      SELECT 1
                      FROM activities
                      WHERE activity_id = ?
                        AND guild_id = ?
                        AND type = 'close'
                        AND status = 'running'
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
            return "disputed"

        except Exception:
            await db.rollback()
            raise
