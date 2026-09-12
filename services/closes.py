import secrets

from dataclasses import dataclass

from database.connection import get_db
from services.close_teams import (
    TEAM_MODE_CAPTAINS,
    TEAM_MODE_RANDOM,
)


@dataclass(frozen=True)
class CloseStartResult:
    status: str
    team_mode: str | None = None
    required: int = 0
    actual: int = 0
    captain_a_id: int | None = None
    captain_b_id: int | None = None
    draft_turn: str | None = None


async def start_close(
    guild_id: int,
    activity_id: int,
) -> CloseStartResult:
    """
    Атомарно запускает CLOSE.

    В одной транзакции проверяет состояние и состав участников,
    формирует команды и переводит активность из open в running.
    """

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            cursor = await db.execute(
                """
                SELECT
                    a.status,
                    a.max_participants,
                    c.team_mode
                FROM activities AS a
                JOIN close_settings AS c
                  ON c.activity_id = a.activity_id
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
                return CloseStartResult(
                    status="not_found"
                )

            status = str(row[0])
            required = (
                int(row[1])
                if row[1] is not None
                else 0
            )
            team_mode = str(row[2])

            if status != "open":
                await db.rollback()
                return CloseStartResult(
                    status="not_open",
                    team_mode=team_mode,
                    required=required,
                )

            if (
                required < 4
                or required % 2 != 0
            ):
                await db.rollback()
                return CloseStartResult(
                    status="invalid_config",
                    team_mode=team_mode,
                    required=required,
                )

            cursor = await db.execute(
                """
                SELECT user_id
                FROM activity_participants
                WHERE activity_id = ?
                ORDER BY joined_at ASC
                """,
                (activity_id,),
            )

            rows = await cursor.fetchall()
            await cursor.close()

            players = [
                int(player_row[0])
                for player_row in rows
            ]
            actual = len(players)

            if actual != required:
                await db.rollback()
                return CloseStartResult(
                    status="wrong_count",
                    team_mode=team_mode,
                    required=required,
                    actual=actual,
                )

            await db.execute(
                """
                UPDATE activity_participants
                SET role = 'participant'
                WHERE activity_id = ?
                """,
                (activity_id,),
            )

            captain_a_id = None
            captain_b_id = None
            draft_turn = None

            if team_mode == TEAM_MODE_RANDOM:
                secrets.SystemRandom().shuffle(players)

                half = len(players) // 2
                team_a = players[:half]
                team_b = players[half:]

                await db.executemany(
                    """
                    UPDATE activity_participants
                    SET role = 'team_a'
                    WHERE activity_id = ?
                      AND user_id = ?
                    """,
                    [
                        (activity_id, user_id)
                        for user_id in team_a
                    ],
                )

                await db.executemany(
                    """
                    UPDATE activity_participants
                    SET role = 'team_b'
                    WHERE activity_id = ?
                      AND user_id = ?
                    """,
                    [
                        (activity_id, user_id)
                        for user_id in team_b
                    ],
                )

                draft_turn = "done"

            elif team_mode == TEAM_MODE_CAPTAINS:
                captain_a_id, captain_b_id = (
                    secrets.SystemRandom().sample(
                        players,
                        2,
                    )
                )

                draft_turn = secrets.choice(
                    ("a", "b")
                )

                await db.execute(
                    """
                    UPDATE activity_participants
                    SET role = 'captain_a'
                    WHERE activity_id = ?
                      AND user_id = ?
                    """,
                    (
                        activity_id,
                        captain_a_id,
                    ),
                )

                await db.execute(
                    """
                    UPDATE activity_participants
                    SET role = 'captain_b'
                    WHERE activity_id = ?
                      AND user_id = ?
                    """,
                    (
                        activity_id,
                        captain_b_id,
                    ),
                )

            else:
                await db.rollback()
                return CloseStartResult(
                    status="invalid_mode",
                    team_mode=team_mode,
                    required=required,
                    actual=actual,
                )

            await db.execute(
                """
                UPDATE close_settings
                SET
                    captain_a_id = ?,
                    captain_b_id = ?,
                    draft_turn = ?
                WHERE activity_id = ?
                """,
                (
                    captain_a_id,
                    captain_b_id,
                    draft_turn,
                    activity_id,
                ),
            )

            cursor = await db.execute(
                """
                UPDATE activities
                SET status = 'running'
                WHERE guild_id = ?
                  AND activity_id = ?
                  AND type = 'close'
                  AND status = 'open'
                """,
                (
                    guild_id,
                    activity_id,
                ),
            )

            changed = cursor.rowcount == 1
            await cursor.close()

            if not changed:
                await db.rollback()
                return CloseStartResult(
                    status="not_open",
                    team_mode=team_mode,
                    required=required,
                    actual=actual,
                )

            await db.commit()

            return CloseStartResult(
                status="started",
                team_mode=team_mode,
                required=required,
                actual=actual,
                captain_a_id=captain_a_id,
                captain_b_id=captain_b_id,
                draft_turn=draft_turn,
            )

        except Exception:
            await db.rollback()
            raise
