from config.leveling import VOICE_XP_PER_MINUTE
from database.connection import get_db
from database.models import MemberStats
from services.progression import calculate_progression


async def get_or_create_member(
    guild_id: int,
    user_id: int,
) -> MemberStats:
    async with get_db() as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO member_stats (
                guild_id,
                user_id
            )
            VALUES (?, ?)
            """,
            (
                guild_id,
                user_id,
            ),
        )

        cursor = await db.execute(
            """
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
              AND user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()
        await db.commit()

    if row is None:
        raise RuntimeError(
            "Не удалось получить статистику участника"
        )

    return MemberStats(
        guild_id=int(row[0]),
        user_id=int(row[1]),
        messages=int(row[2]),
        voice_seconds=int(row[3]),
        xp=int(row[4]),
        currency=int(row[5]),
        eden_cases=int(row[6]),
    )


async def get_member_stats(
    guild_id: int,
    user_id: int,
) -> MemberStats:
    return await get_or_create_member(
        guild_id=guild_id,
        user_id=user_id,
    )


async def record_message(
    guild_id: int,
    user_id: int,
    xp_gain: int = 0,
) -> tuple[int, int]:
    if xp_gain < 0:
        raise ValueError(
            "Начисление XP за сообщение не может быть отрицательным"
        )

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            await db.execute(
                """
                INSERT OR IGNORE INTO member_stats (
                    guild_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            cursor = await db.execute(
                """
                SELECT xp
                FROM member_stats
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                raise RuntimeError(
                    "Не удалось получить XP участника"
                )

            progression = calculate_progression(
                old_xp=int(row[0]),
                xp_gain=xp_gain,
            )

            await db.execute(
                """
                UPDATE member_stats
                SET
                    messages = messages + 1,
                    xp = ?,
                    eden_cases = eden_cases + ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    progression.new_xp,
                    progression.cases_gained,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return (
                progression.cases_gained,
                progression.new_level,
            )

        except Exception:
            await db.rollback()
            raise


async def add_voice_seconds(
    guild_id: int,
    user_id: int,
    seconds: int,
) -> tuple[int, int, int]:
    if seconds <= 0:
        return 0, 0, 1

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            await db.execute(
                """
                INSERT OR IGNORE INTO member_stats (
                    guild_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            cursor = await db.execute(
                """
                SELECT
                    voice_seconds,
                    xp
                FROM member_stats
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                raise RuntimeError(
                    "Не удалось получить статистику участника"
                )

            old_seconds = int(row[0])
            old_xp = int(row[1])
            new_seconds = old_seconds + seconds

            earned_minutes = (
                new_seconds // 60
                - old_seconds // 60
            )

            xp_gain = (
                earned_minutes
                * VOICE_XP_PER_MINUTE
            )

            progression = calculate_progression(
                old_xp=old_xp,
                xp_gain=xp_gain,
            )

            await db.execute(
                """
                UPDATE member_stats
                SET
                    voice_seconds = ?,
                    xp = ?,
                    eden_cases = eden_cases + ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    new_seconds,
                    progression.new_xp,
                    progression.cases_gained,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return (
                xp_gain,
                progression.cases_gained,
                progression.new_level,
            )

        except Exception:
            await db.rollback()
            raise


async def get_member_rank(
    guild_id: int,
    user_id: int,
) -> int:
    stats = await get_or_create_member(
        guild_id=guild_id,
        user_id=user_id,
    )

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM member_stats
            WHERE guild_id = ?
              AND xp > ?
            """,
            (
                guild_id,
                stats.xp,
            ),
        )

        row = await cursor.fetchone()
        await cursor.close()

    if row is None:
        return 1

    return int(row[0]) + 1


async def add_xp(
    guild_id: int,
    user_id: int,
    amount: int,
) -> tuple[int, int, int]:
    if amount <= 0:
        raise ValueError(
            "Количество XP должно быть больше нуля"
        )

    async with get_db() as db:
        try:
            await db.execute("BEGIN IMMEDIATE")

            await db.execute(
                """
                INSERT OR IGNORE INTO member_stats (
                    guild_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            cursor = await db.execute(
                """
                SELECT xp
                FROM member_stats
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                raise RuntimeError(
                    "Не удалось получить XP участника"
                )

            progression = calculate_progression(
                old_xp=int(row[0]),
                xp_gain=amount,
            )

            await db.execute(
                """
                UPDATE member_stats
                SET
                    xp = ?,
                    eden_cases = eden_cases + ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    progression.new_xp,
                    progression.cases_gained,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return (
                progression.new_xp,
                progression.new_level,
                progression.cases_gained,
            )

        except Exception:
            await db.rollback()
            raise


async def ensure_members_exist(
    guild_id: int,
    user_ids: list[int],
) -> None:
    if not user_ids:
        return

    unique_user_ids = list(
        dict.fromkeys(user_ids)
    )

    async with get_db() as db:
        await db.executemany(
            """
            INSERT OR IGNORE INTO member_stats (
                guild_id,
                user_id
            )
            VALUES (?, ?)
            """,
            [
                (
                    guild_id,
                    user_id,
                )
                for user_id in unique_user_ids
            ],
        )

        await db.commit()
