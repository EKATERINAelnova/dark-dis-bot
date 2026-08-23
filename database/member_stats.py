from database.connection import get_db
from database.models import MemberStats
from config.leveling import VOICE_XP_PER_MINUTE


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
                currency
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
) -> None:
    """
    Увеличивает количество сообщений на 1
    и при необходимости начисляет XP.
    """

    if xp_gain < 0:
        raise ValueError(
            "Начисление XP за сообщение "
            "не может быть отрицательным"
        )

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                messages,
                xp
            )
            VALUES (?, ?, 1, ?)

            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                messages = messages + 1,
                xp = xp + excluded.xp
            """,
            (
                guild_id,
                user_id,
                xp_gain,
            ),
        )

        await db.commit()


# =========================================================
# VOICE
# =========================================================

async def add_voice_seconds(
    guild_id: int,
    user_id: int,
    seconds: int,
) -> int:
    """
    Добавляет проведённое в голосовом канале время
    и начисляет XP за полностью завершённые минуты.

    Возвращает количество начисленного XP.
    """

    if seconds <= 0:
        return 0

    async with get_db() as db:
        try:
            # Берём write-lock до чтения текущего времени.
            #
            # Это не позволяет двум параллельным
            # обновлениям voice_seconds прочитать
            # одно и то же старое значение.
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
            # CURRENT VOICE TIME
            # =================================================

            cursor = await db.execute(
                """
                SELECT voice_seconds
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
                    "Не удалось получить voice_seconds"
                )

            old_seconds = int(
                row[0]
            )

            new_seconds = (
                old_seconds
                + seconds
            )

            # =================================================
            # XP
            # =================================================

            # XP начисляется только за новые
            # полностью завершённые минуты.
            #
            # Например:
            #
            # было 59 сек
            # добавили 2 сек
            # стало 61 сек
            #
            # earned_minutes = 1
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

            # =================================================
            # UPDATE
            # =================================================

            await db.execute(
                """
                UPDATE member_stats
                SET
                    voice_seconds = ?,
                    xp = xp + ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    new_seconds,
                    xp_gain,
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