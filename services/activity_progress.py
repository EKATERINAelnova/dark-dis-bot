from dataclasses import dataclass

from database.connection import get_db


@dataclass(frozen=True)
class ActivityProgress:
    participations: int
    wins: int = 0

    @property
    def winrate(self) -> int:
        if self.participations <= 0:
            return 0

        return round(
            self.wins
            / self.participations
            * 100
        )


@dataclass(frozen=True)
class MemberActivityProgress:
    events: ActivityProgress
    duels: ActivityProgress
    closes: ActivityProgress


async def get_event_progress(
    guild_id: int,
    user_id: int,
) -> ActivityProgress:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM activities AS a
            JOIN activity_participants AS p
              ON p.activity_id = a.activity_id
            WHERE a.guild_id = ?
              AND a.type = 'event'
              AND a.status = 'finished'
              AND p.user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    return ActivityProgress(
        participations=(
            int(row[0])
            if row is not None
            else 0
        )
    )


async def get_duel_progress(
    guild_id: int,
    user_id: int,
) -> ActivityProgress:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                COUNT(*),
                SUM(
                    CASE
                        WHEN r.winner_user_id = ?
                        THEN 1
                        ELSE 0
                    END
                )
            FROM activities AS a
            JOIN activity_participants AS p
              ON p.activity_id = a.activity_id
            JOIN activity_results AS r
              ON r.activity_id = a.activity_id
            WHERE a.guild_id = ?
              AND a.type = 'duel'
              AND a.status = 'finished'
              AND r.status = 'confirmed'
              AND p.user_id = ?
            """,
            (
                user_id,
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return ActivityProgress(
            participations=0,
            wins=0,
        )

    return ActivityProgress(
        participations=int(row[0] or 0),
        wins=int(row[1] or 0),
    )


async def get_close_progress(
    guild_id: int,
    user_id: int,
) -> ActivityProgress:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                COUNT(*),
                SUM(
                    CASE
                        WHEN (
                            r.winner_team = 'a'
                            AND p.role IN (
                                'captain_a',
                                'team_a'
                            )
                        )
                        OR (
                            r.winner_team = 'b'
                            AND p.role IN (
                                'captain_b',
                                'team_b'
                            )
                        )
                        THEN 1
                        ELSE 0
                    END
                )
            FROM activities AS a
            JOIN activity_participants AS p
              ON p.activity_id = a.activity_id
            JOIN close_results AS r
              ON r.activity_id = a.activity_id
            WHERE a.guild_id = ?
              AND a.type = 'close'
              AND a.status = 'finished'
              AND r.status = 'confirmed'
              AND p.user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return ActivityProgress(
            participations=0,
            wins=0,
        )

    return ActivityProgress(
        participations=int(row[0] or 0),
        wins=int(row[1] or 0),
    )


async def get_member_activity_progress(
    guild_id: int,
    user_id: int,
) -> MemberActivityProgress:
    events = await get_event_progress(
        guild_id=guild_id,
        user_id=user_id,
    )

    duels = await get_duel_progress(
        guild_id=guild_id,
        user_id=user_id,
    )

    closes = await get_close_progress(
        guild_id=guild_id,
        user_id=user_id,
    )

    return MemberActivityProgress(
        events=events,
        duels=duels,
        closes=closes,
    )
