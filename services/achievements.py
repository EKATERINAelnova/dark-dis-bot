from dataclasses import dataclass

from database.models import MemberStats
from utils.leveling import level_from_xp


@dataclass(frozen=True)
class Achievement:
    name: str
    description: str
    metric: str
    target: int


ACHIEVEMENTS = [
    Achievement(
        name="Первый росток",
        description="Достичь 2 уровня",
        metric="level",
        target=2,
    ),
    Achievement(
        name="Пустить корни",
        description="Достичь 5 уровня",
        metric="level",
        target=5,
    ),
    Achievement(
        name="Шёпот сада",
        description="Отправить 100 сообщений",
        metric="messages",
        target=100,
    ),
    Achievement(
        name="Эхо среди ветвей",
        description="Провести 1 час в голосовых",
        metric="voice",
        target=60 * 60,
    ),
    Achievement(
        name="Следы на земле",
        description="Отправить 1000 сообщений",
        metric="messages",
        target=1000,
    ),
    Achievement(
        name="Глубокие корни",
        description="Провести 10 часов в голосовых",
        metric="voice",
        target=10 * 60 * 60,
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


def get_achievement_progress(
    stats: MemberStats,
) -> list[tuple[Achievement, int, bool]]:
    result = []

    for achievement in ACHIEVEMENTS:
        value = get_achievement_value(
            achievement,
            stats,
        )

        unlocked = (
            value >= achievement.target
        )

        result.append(
            (
                achievement,
                value,
                unlocked,
            )
        )

    return result