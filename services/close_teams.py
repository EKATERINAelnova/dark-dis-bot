import secrets

from dataclasses import dataclass

from database.connection import get_db


TEAM_MODE_RANDOM = "random"
TEAM_MODE_CAPTAINS = "captains"

TEAM_MODES = {
    TEAM_MODE_RANDOM,
    TEAM_MODE_CAPTAINS,
}


@dataclass(frozen=True)
class CloseSettings:
    activity_id: int
    team_mode: str
    captain_a_id: int | None
    captain_b_id: int | None
    draft_turn: str | None


@dataclass(frozen=True)
class CloseTeams:
    team_a: list[int]
    team_b: list[int]
    waiting: list[int]


async def init_close_teams() -> None:
    async with get_db() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS close_settings (
                activity_id INTEGER PRIMARY KEY,
                team_mode TEXT NOT NULL,
                captain_a_id INTEGER,
                captain_b_id INTEGER,
                draft_turn TEXT,

                FOREIGN KEY (activity_id)
                    REFERENCES activities(activity_id)
                    ON DELETE CASCADE
            )
            """
        )

        await db.commit()


async def create_close_settings(
    activity_id: int,
    team_mode: str,
) -> None:
    if team_mode not in TEAM_MODES:
        raise ValueError(
            "Неизвестный режим формирования команд"
        )

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO close_settings (
                activity_id,
                team_mode
            )
            VALUES (?, ?)
            """,
            (
                activity_id,
                team_mode,
            ),
        )

        await db.commit()


async def get_close_settings(
    activity_id: int,
) -> CloseSettings | None:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                activity_id,
                team_mode,
                captain_a_id,
                captain_b_id,
                draft_turn
            FROM close_settings
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

    return CloseSettings(
        activity_id=int(row[0]),
        team_mode=str(row[1]),
        captain_a_id=(
            int(row[2])
            if row[2] is not None
            else None
        ),
        captain_b_id=(
            int(row[3])
            if row[3] is not None
            else None
        ),
        draft_turn=(
            str(row[4])
            if row[4] is not None
            else None
        ),
    )


async def set_close_captains(
    activity_id: int,
    captain_a_id: int,
    captain_b_id: int,
) -> str:
    if captain_a_id == captain_b_id:
        return "same_captain"

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    a.status,
                    c.team_mode
                FROM activities AS a
                JOIN close_settings AS c
                  ON c.activity_id = a.activity_id
                WHERE a.activity_id = ?
                  AND a.type = 'close'
                """,
                (
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

            if str(row[1]) != TEAM_MODE_CAPTAINS:
                await db.rollback()
                return "wrong_mode"

            cursor = await db.execute(
                """
                SELECT user_id
                FROM activity_participants
                WHERE activity_id = ?
                  AND user_id IN (?, ?)
                """,
                (
                    activity_id,
                    captain_a_id,
                    captain_b_id,
                ),
            )

            rows = await cursor.fetchall()
            await cursor.close()

            found = {
                int(item[0])
                for item in rows
            }

            if found != {
                captain_a_id,
                captain_b_id,
            }:
                await db.rollback()
                return "not_participant"

            await db.execute(
                """
                UPDATE close_settings
                SET
                    captain_a_id = ?,
                    captain_b_id = ?,
                    draft_turn = NULL
                WHERE activity_id = ?
                """,
                (
                    captain_a_id,
                    captain_b_id,
                    activity_id,
                ),
            )

            await db.commit()
            return "saved"

        except Exception:
            await db.rollback()
            raise


async def reset_close_roles(
    activity_id: int,
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE activity_participants
            SET role = 'participant'
            WHERE activity_id = ?
            """,
            (
                activity_id,
            ),
        )

        await db.commit()


async def assign_random_teams(
    activity_id: int,
) -> str:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT user_id
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

            players = [
                int(row[0])
                for row in rows
            ]

            if len(players) < 2:
                await db.rollback()
                return "not_enough"

            if len(players) % 2 != 0:
                await db.rollback()
                return "odd_count"

            secrets.SystemRandom().shuffle(
                players
            )

            half = len(players) // 2
            team_a = players[:half]
            team_b = players[half:]

            await db.execute(
                """
                UPDATE activity_participants
                SET role = 'participant'
                WHERE activity_id = ?
                """,
                (
                    activity_id,
                ),
            )

            await db.executemany(
                """
                UPDATE activity_participants
                SET role = 'team_a'
                WHERE activity_id = ?
                  AND user_id = ?
                """,
                [
                    (
                        activity_id,
                        user_id,
                    )
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
                    (
                        activity_id,
                        user_id,
                    )
                    for user_id in team_b
                ],
            )

            await db.execute(
                """
                UPDATE close_settings
                SET draft_turn = 'done'
                WHERE activity_id = ?
                """,
                (
                    activity_id,
                ),
            )

            await db.commit()
            return "assigned"

        except Exception:
            await db.rollback()
            raise


async def prepare_captain_draft(
    activity_id: int,
) -> str:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    captain_a_id,
                    captain_b_id
                FROM close_settings
                WHERE activity_id = ?
                  AND team_mode = 'captains'
                """,
                (
                    activity_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                await db.rollback()
                return "wrong_mode"

            if (
                row[0] is None
                or row[1] is None
            ):
                await db.rollback()
                return "captains_missing"

            captain_a_id = int(row[0])
            captain_b_id = int(row[1])

            cursor = await db.execute(
                """
                SELECT user_id
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

            players = {
                int(item[0])
                for item in rows
            }

            if len(players) < 2:
                await db.rollback()
                return "not_enough"

            if len(players) % 2 != 0:
                await db.rollback()
                return "odd_count"

            if (
                captain_a_id not in players
                or captain_b_id not in players
            ):
                await db.rollback()
                return "captains_missing"

            await db.execute(
                """
                UPDATE activity_participants
                SET role = 'participant'
                WHERE activity_id = ?
                """,
                (
                    activity_id,
                ),
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

            turn = (
                "done"
                if len(players) == 2
                else "a"
            )

            await db.execute(
                """
                UPDATE close_settings
                SET draft_turn = ?
                WHERE activity_id = ?
                """,
                (
                    turn,
                    activity_id,
                ),
            )

            await db.commit()
            return "ready"

        except Exception:
            await db.rollback()
            raise


async def pick_close_player(
    activity_id: int,
    captain_id: int,
    player_id: int,
) -> str:
    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            cursor = await db.execute(
                """
                SELECT
                    a.status,
                    c.captain_a_id,
                    c.captain_b_id,
                    c.draft_turn
                FROM activities AS a
                JOIN close_settings AS c
                  ON c.activity_id = a.activity_id
                WHERE a.activity_id = ?
                  AND a.type = 'close'
                  AND c.team_mode = 'captains'
                """,
                (
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

            captain_a_id = int(row[1])
            captain_b_id = int(row[2])
            turn = str(row[3])

            if turn == "done":
                await db.rollback()
                return "finished"

            expected_captain = (
                captain_a_id
                if turn == "a"
                else captain_b_id
            )

            if captain_id != expected_captain:
                await db.rollback()
                return "wrong_turn"

            cursor = await db.execute(
                """
                SELECT role
                FROM activity_participants
                WHERE activity_id = ?
                  AND user_id = ?
                """,
                (
                    activity_id,
                    player_id,
                ),
            )

            player_row = await cursor.fetchone()
            await cursor.close()

            if player_row is None:
                await db.rollback()
                return "not_participant"

            if str(player_row[0]) != "participant":
                await db.rollback()
                return "already_picked"

            team_role = (
                "team_a"
                if turn == "a"
                else "team_b"
            )

            await db.execute(
                """
                UPDATE activity_participants
                SET role = ?
                WHERE activity_id = ?
                  AND user_id = ?
                  AND role = 'participant'
                """,
                (
                    team_role,
                    activity_id,
                    player_id,
                ),
            )

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

            count_row = await cursor.fetchone()
            await cursor.close()

            waiting = int(count_row[0])

            next_turn = (
                "done"
                if waiting == 0
                else (
                    "b"
                    if turn == "a"
                    else "a"
                )
            )

            await db.execute(
                """
                UPDATE close_settings
                SET draft_turn = ?
                WHERE activity_id = ?
                """,
                (
                    next_turn,
                    activity_id,
                ),
            )

            await db.commit()
            return (
                "finished"
                if next_turn == "done"
                else "picked"
            )

        except Exception:
            await db.rollback()
            raise


async def get_close_teams(
    activity_id: int,
) -> CloseTeams:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                user_id,
                role
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

    team_a = []
    team_b = []
    waiting = []

    for row in rows:
        user_id = int(row[0])
        role = str(row[1])

        if role in {
            "captain_a",
            "team_a",
        }:
            team_a.append(user_id)

        elif role in {
            "captain_b",
            "team_b",
        }:
            team_b.append(user_id)

        else:
            waiting.append(user_id)

    return CloseTeams(
        team_a=team_a,
        team_b=team_b,
        waiting=waiting,
    )
