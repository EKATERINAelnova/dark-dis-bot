from database.connection import get_db
from database.models import MemberStats
from config.leveling import VOICE_XP_PER_MINUTE
from utils.leveling import level_from_xp


# =========================================================
# MEMBER
# =========================================================

async def get_or_create_member(
    guild_id: int,
    user_id: int,
) -> MemberStats:
    """
    Возвращает статистику участника.

    Если участника ещё нет в базе,
    создаёт запись с нулевыми значениями.
    """

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
    """
    Алиас для получения статистики участника.
    """

    return await get_or_create_member(
        guild_id=guild_id,
        user_id=user_id,
    )


# =========================================================
# MESSAGES
# =========================================================

async def record_message(
    guild_id: int,
    user_id: int,
    xp_gain: int = 0,
) -> int:
    """
    Учитывает сообщение и начисляет XP.

    Возвращает количество полученных
    EDEN CASE за новые уровни.
    """

    if xp_gain < 0:
        raise ValueError(
            "Начисление XP за сообщение "
            "не может быть отрицательным"
        )

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

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

            old_xp = int(row[0])
            new_xp = old_xp + xp_gain

            old_level = level_from_xp(
                old_xp
            )

            new_level = level_from_xp(
                new_xp
            )

            cases_gained = max(
                0,
                new_level - old_level,
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
                    new_xp,
                    cases_gained,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return cases_gained

        except Exception:
            await db.rollback()
            raise


# =========================================================
# VOICE
# =========================================================

async def add_voice_seconds(
    guild_id: int,
    user_id: int,
    seconds: int,
) -> int:
    """
    Добавляет проведённое в голосовом канале время,
    начисляет XP за полностью завершённые минуты
    и выдаёт EDEN CASE за новые уровни.

    Возвращает количество начисленного XP.
    """

    if seconds <= 0:
        return 0

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            # =================================================
            # MEMBER
            # =================================================

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

            # =================================================
            # CURRENT STATS
            # =================================================

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

            new_seconds = (
                old_seconds
                + seconds
            )

            # =================================================
            # VOICE XP
            # =================================================

            old_minutes = (
                old_seconds // 60
            )

            new_minutes = (
                new_seconds // 60
            )

            earned_minutes = (
                new_minutes
                - old_minutes
            )

            xp_gain = (
                earned_minutes
                * VOICE_XP_PER_MINUTE
            )

            new_xp = (
                old_xp
                + xp_gain
            )

            # =================================================
            # LEVEL REWARD
            # =================================================

            old_level = level_from_xp(
                old_xp
            )

            new_level = level_from_xp(
                new_xp
            )

            cases_gained = max(
                0,
                new_level - old_level,
            )

            # =================================================
            # UPDATE
            # =================================================

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
                    new_xp,
                    cases_gained,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return xp_gain

        except Exception:
            await db.rollback()
            raise

# =========================================================
# RANK
# =========================================================

async def get_member_rank(
    guild_id: int,
    user_id: int,
) -> int:
    """
    Возвращает позицию участника
    в общем рейтинге по XP.
    """

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


# =========================================================
# XP
# =========================================================

async def add_xp(
    guild_id: int,
    user_id: int,
    amount: int,
) -> tuple[int, int, int]:
    """
    Добавляет XP участнику.

    Возвращает:
    - новый XP;
    - новый уровень;
    - количество полученных EDEN CASE.
    """

    if amount <= 0:
        raise ValueError(
            "Количество XP должно быть больше нуля"
        )

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

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

            old_xp = int(row[0])

            old_level = level_from_xp(
                old_xp
            )

            new_xp = (
                old_xp
                + amount
            )

            new_level = level_from_xp(
                new_xp
            )

            cases_gained = max(
                0,
                new_level - old_level,
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
                    new_xp,
                    cases_gained,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return (
                new_xp,
                new_level,
                cases_gained,
            )

        except Exception:
            await db.rollback()
            raise

# =========================================================
# ENSURE MEMBERS
# =========================================================

async def ensure_members_exist(
    guild_id: int,
    user_ids: list[int],
) -> None:
    """
    Создаёт отсутствующие записи участников.

    Уже существующие данные не изменяются.
    """

    if not user_ids:
        return

    # Убираем возможные дубли,
    # чтобы не отправлять лишние INSERT.
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
                for user_id
                in unique_user_ids
            ],
        )

        await db.commit()