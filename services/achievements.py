import time

from dataclasses import dataclass

from config.economy import REASON_ACHIEVEMENT

from database.connection import get_db
from database.models import MemberStats

from utils.leveling import level_from_xp


@dataclass(frozen=True)
class Achievement:
    key: str
    name: str
    description: str

    metric: str
    target: int

    reward_kind: str
    reward_amount: int


ACHIEVEMENTS = [
    Achievement(
        key="first_sprout",
        name="Первый росток",
        description="Достичь 2 уровня",
        metric="level",
        target=2,
        reward_kind="currency",
        reward_amount=20,
    ),

    Achievement(
        key="rooted",
        name="Пустить корни",
        description="Достичь 5 уровня",
        metric="level",
        target=5,
        reward_kind="case",
        reward_amount=1,
    ),

    Achievement(
        key="garden_whisper",
        name="Шёпот сада",
        description="Отправить 100 сообщений",
        metric="messages",
        target=100,
        reward_kind="currency",
        reward_amount=30,
    ),

    Achievement(
        key="branch_echo",
        name="Эхо среди ветвей",
        description="Провести 1 час в голосовых",
        metric="voice",
        target=60 * 60,
        reward_kind="case",
        reward_amount=1,
    ),

    Achievement(
        key="earth_traces",
        name="Следы на земле",
        description="Отправить 1000 сообщений",
        metric="messages",
        target=1000,
        reward_kind="currency",
        reward_amount=100,
    ),

    Achievement(
        key="deep_roots",
        name="Глубокие корни",
        description="Провести 10 часов в голосовых",
        metric="voice",
        target=10 * 60 * 60,
        reward_kind="case",
        reward_amount=2,
    ),
]


def get_achievement_value(
    achievement: Achievement,
    stats: MemberStats,
) -> int:
    if achievement.metric == "level":
        return level_from_xp(
            stats.xp
        )

    if achievement.metric == "messages":
        return stats.messages

    if achievement.metric == "voice":
        return stats.voice_seconds

    return 0


async def get_unlocked_achievement_keys(
    guild_id: int,
    user_id: int,
) -> set[str]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT achievement_key
            FROM achievement_unlocks
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (
                guild_id,
                user_id,
            ),
        )

        rows = await cursor.fetchall()
        await cursor.close()

    return {
        str(row[0])
        for row in rows
    }


async def check_achievements(
    guild_id: int,
    user_id: int,
) -> list[Achievement]:
    unlocked_now = []

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

            if row is None:
                raise RuntimeError(
                    "Не удалось получить статистику"
                )

            stats = MemberStats(
                guild_id=int(row[0]),
                user_id=int(row[1]),
                messages=int(row[2]),
                voice_seconds=int(row[3]),
                xp=int(row[4]),
                currency=int(row[5]),
                eden_cases=int(row[6]),
            )

            for achievement in ACHIEVEMENTS:
                value = get_achievement_value(
                    achievement,
                    stats,
                )

                if value < achievement.target:
                    continue

                cursor = await db.execute(
                    """
                    INSERT OR IGNORE INTO achievement_unlocks (
                        guild_id,
                        user_id,
                        achievement_key,
                        unlocked_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        user_id,
                        achievement.key,
                        int(time.time()),
                    ),
                )

                was_added = (
                    cursor.rowcount == 1
                )

                await cursor.close()

                if not was_added:
                    continue

                if achievement.reward_kind == "currency":
                    await db.execute(
                        """
                        UPDATE member_stats
                        SET currency = currency + ?
                        WHERE guild_id = ?
                          AND user_id = ?
                        """,
                        (
                            achievement.reward_amount,
                            guild_id,
                            user_id,
                        ),
                    )

                    await db.execute(
                        """
                        INSERT INTO currency_transactions (
                            guild_id,
                            user_id,
                            amount,
                            reason,
                            description,
                            actor_id,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            guild_id,
                            user_id,
                            achievement.reward_amount,
                            REASON_ACHIEVEMENT,
                            achievement.key,
                            None,
                            int(time.time()),
                        ),
                    )

                elif achievement.reward_kind == "case":
                    await db.execute(
                        """
                        UPDATE member_stats
                        SET eden_cases = eden_cases + ?
                        WHERE guild_id = ?
                          AND user_id = ?
                        """,
                        (
                            achievement.reward_amount,
                            guild_id,
                            user_id,
                        ),
                    )

                else:
                    raise RuntimeError(
                        f"Неизвестная награда: "
                        f"{achievement.reward_kind}"
                    )

                unlocked_now.append(
                    achievement
                )

            await db.commit()

            return unlocked_now

        except Exception:
            await db.rollback()
            raise