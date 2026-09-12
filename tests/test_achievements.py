import pytest

from database.connection import get_db
from database.member_stats import get_member_stats
from services.achievement_progress import get_achievement_progress
from services.achievements import (
    check_achievements,
    get_unlocked_achievement_keys,
)


@pytest.mark.asyncio
async def test_achievement_reward_is_granted_only_once(test_db):
    guild_id = 700
    user_id = 77

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                messages
            )
            VALUES (?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                100,
            ),
        )
        await db.commit()

    first = await check_achievements(
        guild_id=guild_id,
        user_id=user_id,
    )
    second = await check_achievements(
        guild_id=guild_id,
        user_id=user_id,
    )

    assert [item.key for item in first] == ["garden_whisper"]
    assert second == []

    stats = await get_member_stats(
        guild_id=guild_id,
        user_id=user_id,
    )
    unlocked = await get_unlocked_achievement_keys(
        guild_id=guild_id,
        user_id=user_id,
    )

    assert stats.currency == 30
    assert unlocked == {"garden_whisper"}


@pytest.mark.asyncio
async def test_achievement_snapshot_reports_progress(test_db):
    guild_id = 701
    user_id = 78

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                messages
            )
            VALUES (?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                40,
            ),
        )
        await db.commit()

    snapshot = await get_achievement_progress(
        guild_id=guild_id,
        user_id=user_id,
        refresh=False,
    )

    garden_whisper = next(
        item
        for item in snapshot.items
        if item.achievement.key == "garden_whisper"
    )

    assert garden_whisper.value == 40
    assert garden_whisper.unlocked is False
    assert snapshot.unlocked_count == 0
    assert snapshot.total_count == len(snapshot.items)
