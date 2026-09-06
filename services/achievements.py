import time

from dataclasses import dataclass

from config.economy import REASON_ACHIEVEMENT
from database.connection import get_db
from database.models import MemberStats
from services.activity_progress import (
    MemberActivityProgress,
    get_member_activity_progress,
)
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
    minimum_participations: int = 0


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

    Achievement(
        key="event_first",
        name="Первый зов",
        description="Завершить первый EVENT как участник",
        metric="event_matches",
        target=1,
        reward_kind="currency",
        reward_amount=15,
    ),
    Achievement(
        key="event_regular",
        name="Там, где собираются души",
        description="Принять участие в 5 завершённых EVENT",
        metric="event_matches",
        target=5,
        reward_kind="currency",
        reward_amount=40,
    ),
    Achievement(
        key="event_veteran",
        name="Свидетель сада",
        description="Принять участие в 20 завершённых EVENT",
        metric="event_matches",
        target=20,
        reward_kind="case",
        reward_amount=1,
    ),

    Achievement(
        key="duel_first_match",
        name="Первый вызов",
        description="Завершить первую подтверждённую DUEL",
        metric="duel_matches",
        target=1,
        reward_kind="currency",
        reward_amount=10,
    ),
    Achievement(
        key="duel_first_win",
        name="Первая зарубка",
        description="Одержать первую победу в DUEL",
        metric="duel_wins",
        target=1,
        reward_kind="currency",
        reward_amount=20,
    ),
    Achievement(
        key="duel_regular",
        name="По лезвию",
        description="Завершить 10 подтверждённых DUEL",
        metric="duel_matches",
        target=10,
        reward_kind="case",
        reward_amount=1,
    ),
    Achievement(
        key="duel_winner",
        name="Имя на коре",
        description="Одержать 10 побед в DUEL",
        metric="duel_wins",
        target=10,
        reward_kind="case",
        reward_amount=1,
    ),
    Achievement(
        key="duel_winrate",
        name="Твёрдая рука",
        description="Держать 65% побед после 10 DUEL",
        metric="duel_winrate",
        target=65,
        reward_kind="currency",
        reward_amount=75,
        minimum_participations=10,
    ),

    Achievement(
        key="close_first_match",
        name="По ту сторону ворот",
        description="Сыграть первый подтверждённый CLOSE",
        metric="close_matches",
        target=1,
        reward_kind="currency",
        reward_amount=15,
    ),
    Achievement(
        key="close_first_win",
        name="Первый разлом",
        description="Одержать первую победу в CLOSE",
        metric="close_wins",
        target=1,
        reward_kind="currency",
        reward_amount=25,
    ),
    Achievement(
        key="close_regular",
        name="Знакомый путь",
        description="Сыграть 10 подтверждённых CLOSE",
        metric="close_matches",
        target=10,
        reward_kind="case",
        reward_amount=1,
    ),
    Achievement(
        key="close_winner",
        name="Сад помнит победителей",
        description="Одержать 10 побед в CLOSE",
        metric="close_wins",
        target=10,
        reward_kind="case",
        reward_amount=1,
    ),
    Achievement(
        key="close_winrate",
        name="Не случайность",
        description="Держать 65% побед после 10 CLOSE",
        metric="close_winrate",
        target=65,
        reward_kind="currency",
        reward_amount=100,
        minimum_participations=10,
    ),
]


def get_achievement_value(
    achievement: Achievement,
    stats: MemberStats,
    activity_progress: MemberActivityProgress | None = None,
) -> int:
    if achievement.metric == "level":
        return level_from_xp(stats.xp)

    if achievement.metric == "messages":
        return stats.messages

    if achievement.metric == "voice":
        return stats.voice_seconds

    if activity_progress is None:
        return 0

    if achievement.metric == "event_matches":
        return activity_progress.events.participations

    if achievement.metric == "duel_matches":
        return activity_progress.duels.participations

    if achievement.metric == "duel_wins":
        return activity_progress.duels.wins

    if achievement.metric == "duel_winrate":
        return activity_progress.duels.winrate

    if achievement.metric == "close_matches":
        return activity_progress.closes.participations

    if achievement.metric == "close_wins":
        return activity_progress.closes.wins

    if achievement.metric == "close_winrate":
        return activity_progress.closes.winrate

    return 0


def get_metric_participations(
    achievement: Achievement,
    activity_progress: MemberActivityProgress,
) -> int:
    if achievement.metric == "duel_winrate":
        return activity_progress.duels.participations

    if achievement.metric == "close_winrate":
        return activity_progress.closes.participations

    return 0


def achievement_is_ready(
    achievement: Achievement,
    value: int,
    activity_progress: MemberActivityProgress,
) -> bool:
    if achievement.minimum_participations > 0:
        if (
            get_metric_participations(
                achievement,
                activity_progress,
            )
            < achievement.minimum_participations
        ):
            return False

    return value >= achievement.target


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
            (guild_id, user_id),
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

    activity_progress = await get_member_activity_progress(
        guild_id=guild_id,
        user_id=user_id,
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
                (guild_id, user_id),
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
                (guild_id, user_id),
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
                    activity_progress,
                )

                if not achievement_is_ready(
                    achievement,
                    value,
                    activity_progress,
                ):
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

                was_added = cursor.rowcount == 1
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

                unlocked_now.append(achievement)

            await db.commit()
            return unlocked_now

        except Exception:
            await db.rollback()
            raise


async def check_activity_participant_achievements(
    guild_id: int,
    activity_id: int,
) -> dict[int, list[Achievement]]:
    async with get_db() as db:
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

    unlocked = {}

    for row in rows:
        user_id = int(row[0])
        unlocked_now = await check_achievements(
            guild_id=guild_id,
            user_id=user_id,
        )

        if unlocked_now:
            unlocked[user_id] = unlocked_now

    return unlocked
